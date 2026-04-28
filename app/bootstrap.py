"""Idempotent bootstrap: create tables + seed reference data + admin user."""
from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .auth import hash_password
from .config import settings
from .db import Base, engine, db_session
from .models import (
    ExtractionRun, GovernanceRule, GovernanceViolation,  # noqa: F401 — needed for SQLAlchemy metadata
    LifecycleStage, Marc, MarcChange, MarcFieldStats, Material,  # noqa: F401
    MaterialPreset, MrpRule, NpdComment, NpdDivision,  # noqa: F401
    NpdEmailEvent, NpdRequest, NpdStep, NpdStepDefinition,  # noqa: F401
    Plant, PresetField, PresetPlant, Product, SchemaMeta, Tag, User,  # noqa: F401
)


SEED_DIR = Path(__file__).resolve().parent.parent / "seed"


def _seed_stages(db: Session) -> None:
    if db.query(LifecycleStage).count() > 0:
        return
    path = SEED_DIR / "stages.csv"
    with path.open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            db.add(
                LifecycleStage(
                    code=row["code"].strip(),
                    label=row["label"].strip(),
                    family=row["family"].strip(),
                    display_order=int(row["display_order"]),
                    color=row["color"].strip(),
                    is_terminal=row["is_terminal"].strip().lower() in ("1", "true", "yes"),
                )
            )


def _seed_plants(db: Session) -> None:
    if db.query(Plant).count() > 0:
        return
    path = SEED_DIR / "plants.csv"
    with path.open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            db.add(
                Plant(
                    plant_code=row["plant_code"].strip(),
                    plant_type=row["plant_type"].strip(),
                    description=row["description"].strip(),
                )
            )


def _seed_mrp_rules(db: Session) -> None:
    if db.query(MrpRule).count() > 0:
        return
    path = SEED_DIR / "mrp_rules.csv"
    with path.open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            plant = row["plant_code"].strip() or None
            db.add(
                MrpRule(
                    plant_code=plant,
                    stage_code=row["stage_code"].strip(),
                    expected_mrp_profile=row["expected_mrp_profile"].strip(),
                )
            )


def _seed_tags(db: Session) -> None:
    if db.query(Tag).count() > 0:
        return
    path = SEED_DIR / "tags.csv"
    if not path.exists():
        return
    with path.open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            db.add(
                Tag(
                    code=row["code"].strip(),
                    label=row["label"].strip(),
                    color=row["color"].strip(),
                    description=row["description"].strip(),
                    display_order=int(row["display_order"]),
                )
            )


def _ensure_admin(db: Session) -> None:
    existing = db.query(User).filter(User.email == settings.admin_email).first()
    if existing:
        return
    db.add(
        User(
            email=settings.admin_email,
            name=settings.admin_name,
            password_hash=hash_password(settings.admin_password),
            role="admin",
            is_active=True,
        )
    )


def _sqlite_has_column(db: Session, table: str, col: str) -> bool:
    rows = db.execute(text(f"PRAGMA table_info({table})")).all()
    return any(r[1] == col for r in rows)


def _migration_add_v2_columns_structural(db: Session) -> None:
    """Phase-1 v2 migration: purely structural ALTER TABLE work.

    Runs BEFORE seed data is loaded so the seed / data-level migrations can
    assume the new columns exist. Idempotent; each ALTER is guarded by a
    column-existence check.
    """
    plan = [
        ("lifecycle_stage", "expected_days", "INTEGER"),
        ("product", "next_review_date", "DATETIME"),
        ("product", "review_note", "TEXT DEFAULT ''"),
        ("stage_transition", "rationale", "TEXT DEFAULT ''"),
        ("stage_transition", "changed_by_id", "INTEGER"),
    ]
    for table, col, coltype in plan:
        if not _sqlite_has_column(db, table, col):
            db.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}"))

    # SQLite can't ALTER COLUMN to drop NOT NULL in place, so rebuild the
    # stage_transition table if its to_snapshot_id is still NOT NULL. We now
    # allow NULL for manual (planner-driven) stage changes that don't belong
    # to any upload snapshot.
    info = db.execute(text("PRAGMA table_info(stage_transition)")).all()
    to_snap_notnull = any(
        r[1] == "to_snapshot_id" and r[3] == 1 for r in info  # notnull flag = col[3]
    )
    if to_snap_notnull:
        db.execute(text("PRAGMA foreign_keys = OFF"))
        db.execute(
            text(
                """
                CREATE TABLE stage_transition_new (
                    id INTEGER PRIMARY KEY,
                    product_id INTEGER NOT NULL,
                    from_stage_code VARCHAR(16),
                    to_stage_code VARCHAR(16) NOT NULL,
                    from_snapshot_id INTEGER,
                    to_snapshot_id INTEGER,
                    detected_at DATETIME NOT NULL,
                    rationale TEXT DEFAULT '',
                    changed_by_id INTEGER,
                    FOREIGN KEY (product_id) REFERENCES product(id),
                    FOREIGN KEY (from_snapshot_id) REFERENCES snapshot(id),
                    FOREIGN KEY (to_snapshot_id) REFERENCES snapshot(id),
                    FOREIGN KEY (changed_by_id) REFERENCES user(id)
                )
                """
            )
        )
        db.execute(
            text(
                """
                INSERT INTO stage_transition_new
                    (id, product_id, from_stage_code, to_stage_code,
                     from_snapshot_id, to_snapshot_id, detected_at,
                     rationale, changed_by_id)
                SELECT id, product_id, from_stage_code, to_stage_code,
                       from_snapshot_id, to_snapshot_id, detected_at,
                       COALESCE(rationale, ''), changed_by_id
                FROM stage_transition
                """
            )
        )
        db.execute(text("DROP TABLE stage_transition"))
        db.execute(text("ALTER TABLE stage_transition_new RENAME TO stage_transition"))
        db.execute(
            text("CREATE INDEX ix_stage_transition_product_id ON stage_transition(product_id)")
        )
        db.execute(text("PRAGMA foreign_keys = ON"))


def _migration_v2_data_seed(db: Session) -> None:
    """Phase-3 v2 migration: data-level changes that need seed rows to exist.

    Currently: seed N2's expected_days = 180 (six months) if still NULL.
    Guarded by schema_meta so it only ever runs once.
    """
    key = "v2_data_seed_v1"
    if db.query(SchemaMeta).filter(SchemaMeta.key == key).first():
        return
    db.execute(
        text(
            "UPDATE lifecycle_stage SET expected_days = 180 "
            "WHERE code = 'N2' AND expected_days IS NULL"
        )
    )
    db.add(SchemaMeta(key=key, value="applied"))


def _migration_drop_new_active_mrp_rules(db: Session) -> None:
    """One-shot: N1/N2/A1 are now considered 'any MRP profile OK'.

    Drop any seeded or previously-created MRP rules for those stages and clear
    stale mismatch flags on the affected products. Tracked in ``schema_meta``
    so this only runs once per database.
    """
    key = "drop_new_active_mrp_rules_v1"
    if db.query(SchemaMeta).filter(SchemaMeta.key == key).first():
        return

    db.query(MrpRule).filter(MrpRule.stage_code.in_(["N1", "N2", "A1"])).delete(
        synchronize_session=False
    )
    # Clear stale flags; next upload will recompute anyway but this keeps the
    # UI honest in the meantime.
    db.query(Product).filter(
        Product.stage_code.in_(["N1", "N2", "A1"]),
        Product.mrp_mismatch.is_(True),
    ).update(
        {"mrp_mismatch": False, "mrp_mismatch_note": ""},
        synchronize_session=False,
    )
    db.add(SchemaMeta(key=key, value="applied"))


def _migration_add_governance_columns(db: Session) -> None:
    """Add snapshot.source column if missing (MDG phase-1 structural migration)."""
    if not _sqlite_has_column(db, "snapshot", "source"):
        db.execute(
            text("ALTER TABLE snapshot ADD COLUMN source VARCHAR(16) NOT NULL DEFAULT 'upload'")
        )


def _seed_governance_rules(db: Session) -> None:
    """Seed governance_rule rows from seed/governance_rules.csv (skip if any exist)."""
    if db.query(GovernanceRule).count() > 0:
        return
    path = SEED_DIR / "governance_rules.csv"
    if not path.exists():
        return
    with path.open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            db.add(
                GovernanceRule(
                    field_name=row["field_name"].strip().upper(),
                    scope_mtart=row["scope_mtart"].strip() or None,
                    scope_plant_code=row["scope_plant_code"].strip() or None,
                    scope_stage_code=row["scope_stage_code"].strip() or None,
                    expected_value=row["expected_value"].strip() or None,
                    allowed_values=row["allowed_values"].strip() or None,
                    severity=row["severity"].strip() or "error",
                )
            )


def _migrate_mrp_rules_into_governance_rules(db: Session) -> None:
    """One-shot: copy existing MrpRule rows into GovernanceRule as DISPR rules.

    Only runs once (tracked in schema_meta). Safe on a fresh DB where
    _seed_governance_rules already wrote the DISPR rules (the guard prevents
    doubling up because we skip if any GovernanceRule rows exist in seeding,
    and skip here if schema_meta key already set).
    """
    key = "migrate_mrp_rules_to_governance_v1"
    if db.query(SchemaMeta).filter(SchemaMeta.key == key).first():
        return
    for rule in db.scalars(select(MrpRule)).all():
        # Check if an equivalent governance rule already exists
        existing = (
            db.query(GovernanceRule)
            .filter(
                GovernanceRule.field_name == "DISPR",
                GovernanceRule.scope_plant_code == rule.plant_code,
                GovernanceRule.scope_stage_code == rule.stage_code,
            )
            .first()
        )
        if not existing:
            db.add(
                GovernanceRule(
                    field_name="DISPR",
                    scope_mtart=None,
                    scope_plant_code=rule.plant_code,
                    scope_stage_code=rule.stage_code,
                    expected_value=None,
                    allowed_values=rule.expected_mrp_profile,
                    severity="error",
                )
            )
    db.add(SchemaMeta(key=key, value="applied"))


def _seed_npd_divisions(db: Session) -> None:
    """Seed NPD business divisions."""
    if db.query(NpdDivision).count() > 0:
        return
    for code, label in [
        ("54", "Refinish"),
        ("55", "Protective Coatings"),
        ("75", "Avista"),
    ]:
        db.add(NpdDivision(code=code, label=label))


def _seed_npd_step_definitions(db: Session) -> None:
    """Seed the 10 standard NPD step definitions."""
    if db.query(NpdStepDefinition).count() > 0:
        return
    steps = [
        (1, "warehouse_ext", "Warehouse Extension", True, "[]",
         "Extend the material to all required warehouse plants in SAP so it can be received and stored."),
        (2, "bulk_master_data", "Bulk Master Data", True, '["bulk_fg","bulk_only"]',
         "Complete all SAP MARC/MRP master data for the bulk material including MRP type, lot sizes and procurement type."),
        (3, "fg_master_data", "FG Master Data Complete", True, '["bulk_fg","fg_only"]',
         "Complete all SAP MARC/MRP master data for the finished-goods material."),
        (4, "fg_routings", "FG Routings Setup", True, '["bulk_fg","fg_only"]',
         "Create or extend production routings for the FG material so the production order can be costed and scheduled."),
        (5, "fg_warehouse_ext", "FG Warehouse Extension", False, '["bulk_fg","fg_only"]',
         "Extend the FG material to warehouse plants so it can be shipped and received after production."),
        (6, "costings", "Costings Complete", True, "[]",
         "Standard cost estimate run and marked in SAP; costing cockpit sign-off completed."),
        (7, "ebr_ready", "EBR Ready (Experimental Batch)", False, "[]",
         "All pre-requisites for the experimental/trial batch are confirmed; EBR document approved."),
        (8, "master_data_check", "Master Data Check", True, "[]",
         "Final master data review gate: all critical MARC fields validated against governance presets."),
        (9, "batch_raised", "Batch Raised", False, "[]",
         "The first production batch has been raised (process order created) in SAP."),
        (10, "batch_scheduled", "Batch Scheduled", True, "[]",
         "The production batch has a confirmed scheduled date and has been communicated to the plant."),
    ]
    for sort, code, label, blocking, applies_to, description in steps:
        db.add(NpdStepDefinition(
            step_code=code,
            label=label,
            description=description,
            is_blocking=blocking,
            applies_to=applies_to,
            sort_order=sort,
        ))


def _seed_default_presets(db: Session) -> None:
    """Seed 7 default material presets (no fields — admin configures fields in UI)."""
    if db.query(MaterialPreset).count() > 0:
        return
    for code, label, order in [
        ("bulk", "Bulk", 1),
        ("packaging", "Packaging", 2),
        ("fg_factory", "Finished Good at Factory", 3),
        ("mto_factory", "Make to Order at Factory", 4),
        ("intermediate", "Intermediate", 5),
        ("fg_warehouse", "Finished Good at Warehouse", 6),
        ("mto_warehouse", "Make to Order at Warehouse", 7),
    ]:
        db.add(MaterialPreset(
            preset_code=code,
            label=label,
            description="",
            display_order=order,
        ))


def _migration_add_npd_tables(db: Session) -> None:
    """One-shot guard: new NPD tables are created by Base.metadata.create_all in bootstrap()."""
    key = "npd_tables_v1"
    if db.query(SchemaMeta).filter(SchemaMeta.key == key).first():
        return
    # create_all is idempotent and already called at the top of bootstrap()
    Base.metadata.create_all(bind=engine)
    db.add(SchemaMeta(key=key, value="applied"))


def bootstrap() -> None:
    """Create tables and seed data. Safe to call on every startup."""
    Base.metadata.create_all(bind=engine)
    with db_session() as db:
        # Phase 1: schema migrations (ALTER TABLE etc.) that only touch
        # structural columns. Safe to run before reference data exists.
        _migration_add_v2_columns_structural(db)
        _migration_add_governance_columns(db)
        db.flush()

        # Phase 2: seed reference data.
        _seed_stages(db)
        db.flush()
        _seed_plants(db)
        db.flush()
        _seed_npd_divisions(db)
        db.flush()
        _seed_npd_step_definitions(db)
        db.flush()
        _seed_default_presets(db)
        db.flush()
        _seed_mrp_rules(db)
        db.flush()
        _seed_tags(db)
        _seed_governance_rules(db)
        db.flush()
        _ensure_admin(db)
        db.flush()

        # Phase 3: data-dependent migrations (need stages/etc. to exist).
        _migration_v2_data_seed(db)
        _migration_drop_new_active_mrp_rules(db)
        _migrate_mrp_rules_into_governance_rules(db)
        _migration_add_npd_tables(db)
