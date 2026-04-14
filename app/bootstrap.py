"""Idempotent bootstrap: create tables + seed reference data + admin user."""
from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import hash_password
from .config import settings
from .db import Base, engine, db_session
from .models import LifecycleStage, MrpRule, Plant, Product, SchemaMeta, Tag, User


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


def bootstrap() -> None:
    """Create tables and seed data. Safe to call on every startup."""
    Base.metadata.create_all(bind=engine)
    with db_session() as db:
        # Phase 1: schema migrations (ALTER TABLE etc.) that only touch
        # structural columns. Safe to run before reference data exists.
        _migration_add_v2_columns_structural(db)
        db.flush()

        # Phase 2: seed reference data.
        _seed_stages(db)
        db.flush()
        _seed_plants(db)
        db.flush()
        _seed_mrp_rules(db)
        db.flush()
        _seed_tags(db)
        _ensure_admin(db)
        db.flush()

        # Phase 3: data-dependent migrations (need stages/etc. to exist).
        _migration_v2_data_seed(db)
        _migration_drop_new_active_mrp_rules(db)
