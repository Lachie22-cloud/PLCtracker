"""Upload pipeline: parse -> record snapshot -> upsert products -> diff -> validate.

The public entry point is :func:`process_upload`.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    LifecycleStage,
    MrpRule,
    Plant,
    Product,
    Snapshot,
    SnapshotRow,
    StageTransition,
)


# ---------------------------------------------------------------------------
# Column mapping / parsing
# ---------------------------------------------------------------------------

# Accepted spellings for the four SAP columns we care about. Lowercased /
# stripped before comparison.
COLUMN_ALIASES: Dict[str, List[str]] = {
    "material_no": ["material", "matnr", "material_no", "material number"],
    "plant_code": ["plant", "werks", "plant_code"],
    "stage_code": [
        "plant-sp.matl status",
        "plant-sp. matl status",
        "plant-specific material status",
        "plant sp matl status",
        "stage",
        "status",
        "mstae",
        "plant-sp status",
    ],
    "mrp_profile": ["mrp profile", "mrp_profile", "mrp", "profile"],
}


class UploadParseError(ValueError):
    """Raised when the uploaded file can't be parsed into the expected columns."""


def _normalize_header(h: str) -> str:
    return (h or "").strip().lower()


def _resolve_columns(headers: List[str]) -> Dict[str, str]:
    """Map our canonical field names to the actual header string in the file."""
    normalized = {_normalize_header(h): h for h in headers}
    resolved: Dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                resolved[canonical] = normalized[alias]
                break
        else:
            raise UploadParseError(
                f"Missing required column for '{canonical}'. Expected one of: "
                f"{', '.join(aliases)}"
            )
    return resolved


def parse_upload_bytes(content: bytes, filename: str) -> pd.DataFrame:
    """Return a DataFrame with canonical columns:
    material_no, plant_code, stage_code, mrp_profile."""
    suffix = Path(filename).suffix.lower()
    if suffix in (".xlsx", ".xls"):
        df = pd.read_excel(io.BytesIO(content), dtype=str)
    else:
        # Default to CSV; try utf-8 first, fall back to latin-1 for Excel exports
        try:
            df = pd.read_csv(io.BytesIO(content), dtype=str)
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(content), dtype=str, encoding="latin-1")

    if df.empty:
        raise UploadParseError("Uploaded file is empty.")

    mapping = _resolve_columns(list(df.columns))
    # Rename to canonical and keep only those columns
    df = df.rename(columns={v: k for k, v in mapping.items()})[list(mapping.keys())]
    # Strip whitespace / uppercase stage codes (SAP is consistent uppercase)
    for col in df.columns:
        df[col] = df[col].fillna("").astype(str).str.strip()
    df["stage_code"] = df["stage_code"].str.upper()
    df["plant_code"] = df["plant_code"].str.upper()
    df["mrp_profile"] = df["mrp_profile"].str.upper()

    # Drop rows that are effectively blank on the key fields
    df = df[(df["material_no"] != "") & (df["plant_code"] != "") & (df["stage_code"] != "")]
    df = df.reset_index(drop=True)

    if df.empty:
        raise UploadParseError("Uploaded file contained no usable rows.")

    return df


# ---------------------------------------------------------------------------
# MRP rule lookup
# ---------------------------------------------------------------------------


@dataclass
class MrpRuleIndex:
    plant_specific: Dict[Tuple[str, str], str] = field(default_factory=dict)
    plant_agnostic: Dict[str, str] = field(default_factory=dict)

    def expected(self, plant: str, stage: str) -> Optional[str]:
        v = self.plant_specific.get((plant, stage))
        if v is not None:
            return v
        return self.plant_agnostic.get(stage)


def load_mrp_rules(db: Session) -> MrpRuleIndex:
    idx = MrpRuleIndex()
    for rule in db.scalars(select(MrpRule)).all():
        if rule.plant_code:
            idx.plant_specific[(rule.plant_code, rule.stage_code)] = rule.expected_mrp_profile
        else:
            idx.plant_agnostic[rule.stage_code] = rule.expected_mrp_profile
    return idx


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


@dataclass
class UploadSummary:
    snapshot_id: int
    row_count: int
    added: int = 0
    updated: int = 0
    stage_changed: int = 0
    removed: int = 0
    mrp_mismatches: int = 0
    family_mismatches: int = 0
    unknown_plants: List[str] = field(default_factory=list)
    unknown_stages: List[str] = field(default_factory=list)


def _ensure_plants(db: Session, plants: List[str]) -> List[str]:
    existing = {p.plant_code for p in db.scalars(select(Plant)).all()}
    unknown = sorted(set(plants) - existing)
    # Auto-create as 'warehouse' (default). Admin can relabel later.
    for code in unknown:
        db.add(Plant(plant_code=code, plant_type="warehouse", description=f"Auto-added {code}"))
    if unknown:
        db.flush()
    return unknown


def _ensure_stages(db: Session, stages: List[str]) -> List[str]:
    existing = {s.code for s in db.scalars(select(LifecycleStage)).all()}
    unknown = sorted(set(stages) - existing)
    # Auto-create unknown stages so upload doesn't fail; admin can relabel later.
    for i, code in enumerate(unknown):
        db.add(
            LifecycleStage(
                code=code,
                label=code,
                family="Unclassified",
                display_order=1000 + i,
                color="#d1d5db",
                is_terminal=False,
            )
        )
    if unknown:
        db.flush()
    return unknown


def process_upload(
    db: Session,
    *,
    content: bytes,
    filename: str,
    uploaded_by_id: int,
) -> UploadSummary:
    df = parse_upload_bytes(content, filename)

    unknown_plants = _ensure_plants(db, df["plant_code"].unique().tolist())
    unknown_stages = _ensure_stages(db, df["stage_code"].unique().tolist())

    snapshot = Snapshot(
        uploaded_by_id=uploaded_by_id,
        filename=filename,
        row_count=len(df),
    )
    db.add(snapshot)
    db.flush()  # so snapshot.id is populated

    # Immutable snapshot rows
    db.bulk_save_objects(
        [
            SnapshotRow(
                snapshot_id=snapshot.id,
                material_no=r.material_no,
                plant_code=r.plant_code,
                stage_code=r.stage_code,
                mrp_profile=r.mrp_profile,
            )
            for r in df.itertuples(index=False)
        ]
    )

    # Load all existing products keyed by (material_no, plant_code)
    existing_products: Dict[Tuple[str, str], Product] = {
        (p.material_no, p.plant_code): p for p in db.scalars(select(Product)).all()
    }

    mrp_index = load_mrp_rules(db)
    now = datetime.utcnow()
    summary = UploadSummary(
        snapshot_id=snapshot.id,
        row_count=len(df),
        unknown_plants=unknown_plants,
        unknown_stages=unknown_stages,
    )

    seen_keys: set[Tuple[str, str]] = set()
    transitions: List[StageTransition] = []

    for row in df.itertuples(index=False):
        key = (row.material_no, row.plant_code)
        seen_keys.add(key)
        prior = existing_products.get(key)

        expected_mrp = mrp_index.expected(row.plant_code, row.stage_code)
        if expected_mrp is None:
            mrp_mismatch = False
            mrp_note = "No MRP rule configured for this status at this plant."
        elif expected_mrp != row.mrp_profile:
            mrp_mismatch = True
            mrp_note = (
                f"Expected MRP profile '{expected_mrp}' for status "
                f"{row.stage_code} at plant {row.plant_code}, got '{row.mrp_profile}'."
            )
            summary.mrp_mismatches += 1
        else:
            mrp_mismatch = False
            mrp_note = ""

        if prior is None:
            product = Product(
                material_no=row.material_no,
                plant_code=row.plant_code,
                stage_code=row.stage_code,
                mrp_profile=row.mrp_profile,
                mrp_mismatch=mrp_mismatch,
                mrp_mismatch_note=mrp_note,
                first_seen_at=now,
                last_seen_at=now,
                stage_since=now,
            )
            db.add(product)
            db.flush()
            summary.added += 1
            transitions.append(
                StageTransition(
                    product_id=product.id,
                    from_stage_code=None,
                    to_stage_code=row.stage_code,
                    from_snapshot_id=None,
                    to_snapshot_id=snapshot.id,
                    detected_at=now,
                )
            )
            existing_products[key] = product
        else:
            stage_changed = prior.stage_code != row.stage_code
            prior.mrp_profile = row.mrp_profile
            prior.mrp_mismatch = mrp_mismatch
            prior.mrp_mismatch_note = mrp_note
            prior.last_seen_at = now
            if stage_changed:
                transitions.append(
                    StageTransition(
                        product_id=prior.id,
                        from_stage_code=prior.stage_code,
                        to_stage_code=row.stage_code,
                        from_snapshot_id=None,  # prior snapshot id not tracked on product
                        to_snapshot_id=snapshot.id,
                        detected_at=now,
                    )
                )
                prior.stage_code = row.stage_code
                prior.stage_since = now
                summary.stage_changed += 1
            summary.updated += 1

    if transitions:
        db.add_all(transitions)

    # Products that were in the DB but not in this upload
    missing_keys = set(existing_products.keys()) - seen_keys
    summary.removed = len(missing_keys)
    # We don't hard-delete; just record by leaving them alone. They retain their
    # stage and are visible in the board. Future: mark as "last seen at" old.
    # Downstream reporting can filter on last_seen_at < snapshot.uploaded_at.

    # --- Family-status mismatch pass --------------------------------------
    summary.family_mismatches = _recompute_family_mismatches(db)

    db.flush()
    return summary


def _recompute_family_mismatches(db: Session) -> int:
    """For each material_no, compare factory vs warehouse stage codes.

    Returns total count of products marked with a family mismatch.
    """
    plants = {p.plant_code: p for p in db.scalars(select(Plant)).all()}

    # Group products by material
    all_products: List[Product] = list(db.scalars(select(Product)).all())
    by_material: Dict[str, List[Product]] = {}
    for p in all_products:
        by_material.setdefault(p.material_no, []).append(p)

    mismatch_count = 0
    for material_no, rows in by_material.items():
        factory_rows = [r for r in rows if plants.get(r.plant_code) and plants[r.plant_code].plant_type == "factory"]
        warehouse_rows = [r for r in rows if plants.get(r.plant_code) and plants[r.plant_code].plant_type == "warehouse"]

        if not factory_rows or not warehouse_rows:
            # Can't compare; clear flags
            for r in rows:
                r.family_mismatch = False
                r.family_mismatch_note = ""
            continue

        # If the factory has multiple rows (e.g. multiple factory plants), take
        # the "latest" stage by display_order as the authoritative one — but
        # typically there's only one factory plant per material.
        factory_stages = {r.stage_code for r in factory_rows}
        factory_plants = sorted({r.plant_code for r in factory_rows})

        # Clear factory rows' flag; they're the authority
        for r in factory_rows:
            r.family_mismatch = False
            r.family_mismatch_note = ""

        for wh in warehouse_rows:
            if wh.stage_code in factory_stages:
                wh.family_mismatch = False
                wh.family_mismatch_note = ""
            else:
                wh.family_mismatch = True
                wh.family_mismatch_note = (
                    f"Factory {'/'.join(factory_plants)} is "
                    f"{'/'.join(sorted(factory_stages))}; this warehouse "
                    f"({wh.plant_code}) is still {wh.stage_code} — review data."
                )
                mismatch_count += 1

    return mismatch_count
