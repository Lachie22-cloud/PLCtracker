"""Extraction orchestrator: OData → material/marc upsert → governance → PLC sync."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import db_session
from ..models import (
    ExtractionRun,
    GovernanceViolation,
    Marc,
    MarcChange,
    Material,
    Plant,
    Product,
    StageTransition,
)
from .governance import MARC_FIELDS, load_rules, rebuild_violations
from .sap_odata import MARC_FIELD_MAP, SapODataClient
from .snapshot import _ensure_plants, _ensure_stages, _recompute_family_mismatches

logger = logging.getLogger(__name__)


@dataclass
class ExtractionSummary:
    run_id: int
    source: str
    mara_count: int = 0
    marc_count: int = 0
    change_count: int = 0
    violation_count: int = 0
    error: Optional[str] = None


def _str(value: Any) -> str:
    """Normalise OData value to a plain string."""
    if value is None:
        return ""
    return str(value).strip()


def _upsert_material(db: Session, row: Dict[str, Any], now: datetime) -> Tuple[Material, bool]:
    matnr = _str(row.get("Material"))
    if not matnr:
        raise ValueError("MARA row missing Material key")
    existing = db.get(Material, matnr)
    if existing is None:
        mat = Material(
            matnr=matnr,
            mtart=_str(row.get("MaterialType")),
            mbrsh=_str(row.get("IndustrySector")),
            maktx=_str(row.get("MaterialName")),
            meins=_str(row.get("BaseUnit")),
            matkl=_str(row.get("MaterialGroup")),
            ersda=_str(row.get("CreationDate")),
            laeda=_str(row.get("LastChangeDate")),
            first_seen_at=now,
            last_seen_at=now,
        )
        db.add(mat)
        return mat, True
    else:
        existing.mtart = _str(row.get("MaterialType"))
        existing.mbrsh = _str(row.get("IndustrySector"))
        existing.maktx = _str(row.get("MaterialName"))
        existing.meins = _str(row.get("BaseUnit"))
        existing.matkl = _str(row.get("MaterialGroup"))
        existing.laeda = _str(row.get("LastChangeDate"))
        existing.last_seen_at = now
        return existing, False


def _upsert_marc(
    db: Session,
    row: Dict[str, Any],
    now: datetime,
    run_id: int,
) -> Tuple[Marc, int]:
    """Upsert one MARC row. Returns (marc_obj, change_count)."""
    matnr = _str(row.get("Material"))
    werks = _str(row.get("Plant")).upper()
    if not matnr or not werks:
        raise ValueError("MARC row missing Material or Plant key")

    new_vals: Dict[str, str] = {}
    for odata_key, attr in MARC_FIELD_MAP.items():
        new_vals[attr] = _str(row.get(odata_key))

    existing = db.get(Marc, (matnr, werks))
    changes = 0

    if existing is None:
        marc = Marc(matnr=matnr, werks=werks, first_seen_at=now, last_seen_at=now)
        for attr, val in new_vals.items():
            setattr(marc, attr, val or None)
        db.add(marc)
    else:
        for attr, new_val in new_vals.items():
            old_val = getattr(existing, attr, None) or ""
            new_val_norm = new_val or ""
            if old_val != new_val_norm:
                db.add(
                    MarcChange(
                        matnr=matnr,
                        werks=werks,
                        field_name=attr.upper(),
                        old_value=old_val or None,
                        new_value=new_val_norm or None,
                        extraction_run_id=run_id,
                        detected_at=now,
                    )
                )
                setattr(existing, attr, new_val_norm or None)
                changes += 1
        existing.last_seen_at = now
        marc = existing

    return marc, changes


def _sync_products_from_marc(db: Session, now: datetime) -> None:
    """Project MARC state into the product + stage_transition tables."""
    marc_rows: List[Marc] = list(db.scalars(select(Marc)).all())
    mtart_by_matnr: Dict[str, str] = {
        m.matnr: m.mtart for m in db.scalars(select(Material)).all()
    }

    # Gather all plant codes and stage codes from MARC
    plant_codes = list({m.werks for m in marc_rows})
    stage_codes = [m.mmsta for m in marc_rows if m.mmsta]
    _ensure_plants(db, plant_codes)
    _ensure_stages(db, stage_codes)
    db.flush()

    existing_products: Dict[Tuple[str, str], Product] = {
        (p.material_no, p.plant_code): p
        for p in db.scalars(select(Product)).all()
    }

    # Load governance violations for MRP mismatch flag
    open_violations_dispr: Dict[Tuple[str, str], GovernanceViolation] = {}
    for v in db.scalars(
        select(GovernanceViolation).where(
            GovernanceViolation.field_name == "DISPR",
            GovernanceViolation.resolved_at.is_(None),
        )
    ).all():
        open_violations_dispr[(v.matnr, v.werks)] = v

    for marc in marc_rows:
        if not marc.mmsta:
            continue
        key = (marc.matnr, marc.werks)
        prior = existing_products.get(key)
        dispr_viol = open_violations_dispr.get(key)

        mrp_mismatch = dispr_viol is not None
        mrp_note = dispr_viol.note if dispr_viol else ""

        if prior is None:
            product = Product(
                material_no=marc.matnr,
                plant_code=marc.werks,
                stage_code=marc.mmsta,
                mrp_profile=marc.dispr or "",
                mrp_mismatch=mrp_mismatch,
                mrp_mismatch_note=mrp_note,
                first_seen_at=now,
                last_seen_at=now,
                stage_since=now,
            )
            db.add(product)
            db.flush()
            db.add(
                StageTransition(
                    product_id=product.id,
                    from_stage_code=None,
                    to_stage_code=marc.mmsta,
                    from_snapshot_id=None,
                    to_snapshot_id=None,
                    detected_at=now,
                )
            )
            existing_products[key] = product
        else:
            stage_changed = prior.stage_code != marc.mmsta
            prior.mrp_profile = marc.dispr or ""
            prior.mrp_mismatch = mrp_mismatch
            prior.mrp_mismatch_note = mrp_note
            prior.last_seen_at = now
            if stage_changed:
                db.add(
                    StageTransition(
                        product_id=prior.id,
                        from_stage_code=prior.stage_code,
                        to_stage_code=marc.mmsta,
                        from_snapshot_id=None,
                        to_snapshot_id=None,
                        detected_at=now,
                    )
                )
                prior.stage_code = marc.mmsta
                prior.stage_since = now

    _recompute_family_mismatches(db)


def run_extraction(
    *,
    source: str = "odata",
    trigger: str = "scheduler",
    client: Optional[SapODataClient] = None,
    db: Optional[Session] = None,
) -> ExtractionSummary:
    """Run one full extraction cycle. Thread-safe; opens its own DB session if not given.

    Args:
        source: 'odata' or 'upload'
        trigger: free-form label ('scheduler', 'manual', etc.)
        client: override for testing (mock httpx transport)
        db: override for testing (pass an existing session)
    """

    def _run(db: Session) -> ExtractionSummary:
        now = datetime.utcnow()
        run = ExtractionRun(source=source, started_at=now, status="running")
        db.add(run)
        db.flush()

        summary = ExtractionSummary(run_id=run.id, source=source)

        try:
            own_client = client is None
            _client = client or SapODataClient()
            try:
                for mara_row in _client.iter_mara():
                    _upsert_material(db, mara_row, now)
                    summary.mara_count += 1
                db.flush()

                for marc_row in _client.iter_marc():
                    _, changes = _upsert_marc(db, marc_row, now, run.id)
                    summary.marc_count += 1
                    summary.change_count += changes
                db.flush()

            finally:
                if own_client:
                    _client.close()

            rule_index = load_rules(db)
            summary.violation_count = rebuild_violations(db, rule_index)

            _sync_products_from_marc(db, now)

            run.mara_count = summary.mara_count
            run.marc_count = summary.marc_count
            run.change_count = summary.change_count
            run.finished_at = datetime.utcnow()
            run.status = "success"

        except Exception as exc:
            logger.exception("Extraction run %d failed: %s", run.id, exc)
            run.status = "error"
            run.error_text = str(exc)
            run.finished_at = datetime.utcnow()
            summary.error = str(exc)

        db.flush()
        return summary

    if db is not None:
        return _run(db)

    with db_session() as session:
        return _run(session)
