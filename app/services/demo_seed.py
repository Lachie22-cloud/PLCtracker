"""Demo data seed — loads a full realistic dataset for demonstration purposes."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import hash_password
from ..models import (
    Marc,
    MarcFieldStats,
    Material,
    MaterialPreset,
    NpdComment,
    NpdEmailEvent,
    NpdRequest,
    NpdStep,
    NpdStepDefinition,
    Plant,
    PresetField,
    PresetPlant,
    Product,
    SchemaMeta,
    StageTransition,
    Tag,
    User,
)
from .governance import load_presets, rebuild_violations, sync_preset_fields_to_rules

DEMO_KEY = "demo_data_v1"

_NOW = datetime.utcnow()


def _ago(days: int) -> datetime:
    return _NOW - timedelta(days=days)


def _date_ago(days: int) -> date:
    return (_NOW - timedelta(days=days)).date()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_or_create_user(db: Session, email: str, name: str, role: str) -> User:
    u = db.query(User).filter(User.email == email).first()
    if u:
        return u
    u = User(email=email, name=name, password_hash=hash_password("demo1234"), role=role, is_active=True)
    db.add(u)
    db.flush()
    return u


def _ensure_plant(db: Session, code: str, plant_type: str, description: str) -> Plant:
    p = db.get(Plant, code)
    if p:
        p.plant_type = plant_type
        p.description = description
        return p
    p = Plant(plant_code=code, plant_type=plant_type, description=description)
    db.add(p)
    db.flush()
    return p


def _make_material(db: Session, matnr: str, mtart: str, maktx: str, matkl: str) -> Material:
    m = db.get(Material, matnr)
    if m:
        return m
    m = Material(
        matnr=matnr, mtart=mtart, mbrsh="C", maktx=maktx, meins="L",
        matkl=matkl, ersda="20240101", laeda="20260101",
        first_seen_at=_ago(60), last_seen_at=_NOW,
    )
    db.add(m)
    db.flush()
    return m


def _make_marc(
    db: Session, matnr: str, werks: str, mmsta: str,
    dismm: str = "PD", dispo: str = "100", strgr: str = "40",
    beskz: str = "E", dispr: str = "MTSF", losfx: Optional[str] = None,
    eisbe: Optional[str] = None,
) -> Marc:
    existing = db.get(Marc, (matnr, werks))
    if existing:
        return existing
    marc = Marc(
        matnr=matnr, werks=werks, mmsta=mmsta,
        dismm=dismm, dispo=dispo, strgr=strgr, beskz=beskz,
        dispr=dispr, losfx=losfx, eisbe=eisbe,
        first_seen_at=_ago(60), last_seen_at=_NOW,
    )
    db.add(marc)
    db.flush()
    return marc


def _make_product(
    db: Session, material_no: str, plant_code: str, stage_code: str,
    mrp_profile: str, stage_since_days: int, owner: Optional[User] = None,
    mrp_mismatch: bool = False, family_mismatch: bool = False,
) -> Product:
    existing = (
        db.query(Product)
        .filter(Product.material_no == material_no, Product.plant_code == plant_code)
        .first()
    )
    if existing:
        return existing
    p = Product(
        material_no=material_no, plant_code=plant_code, stage_code=stage_code,
        mrp_profile=mrp_profile, owner_id=owner.id if owner else None,
        mrp_mismatch=mrp_mismatch, mrp_mismatch_note="MRP profile mismatch detected" if mrp_mismatch else "",
        family_mismatch=family_mismatch,
        family_mismatch_note="Stage differs from factory plant" if family_mismatch else "",
        first_seen_at=_ago(60), last_seen_at=_NOW,
        stage_since=_ago(stage_since_days),
    )
    db.add(p)
    db.flush()
    db.add(StageTransition(
        product_id=p.id, from_stage_code=None, to_stage_code=stage_code,
        detected_at=_ago(stage_since_days),
    ))
    return p


def _make_npd(
    db: Session, request_no: str, request_type: str, request_from: str,
    division_code: str, bulk_sku: Optional[str], fg_sku: Optional[str],
    warehouse_plants: list[str], target_date: Optional[date],
    entered_by: User, status: str, created_days_ago: int,
    steps_completed: list[str], notes: str = "",
) -> NpdRequest:
    existing = db.query(NpdRequest).filter(NpdRequest.request_no == request_no).first()
    if existing:
        return existing

    req = NpdRequest(
        request_no=request_no, status=status, request_type=request_type,
        request_from=request_from, division_code=division_code,
        entered_by_id=entered_by.id,
        created_at=_ago(created_days_ago),
        target_date=target_date, bulk_sku=bulk_sku, fg_sku=fg_sku,
        warehouse_plants=json.dumps(warehouse_plants), notes=notes,
    )
    db.add(req)
    db.flush()

    # Create steps from definitions
    step_defs = {
        s.step_code: s
        for s in db.scalars(select(NpdStepDefinition)).all()
    }
    applies_map = {
        code: json.loads(sd.applies_to) for code, sd in step_defs.items()
    }

    for code, sd in sorted(step_defs.items(), key=lambda x: x[1].sort_order):
        applies_to = applies_map.get(code, [])
        is_na = bool(applies_to) and request_type not in applies_to
        if is_na:
            step_status = "n_a"
        elif code in steps_completed:
            step_status = "completed"
        else:
            step_status = "not_started"

        completed_at = None
        completed_by_id = None
        if step_status == "completed":
            idx = steps_completed.index(code)
            completed_at = _ago(created_days_ago - (idx + 1) * 3)
            completed_by_id = entered_by.id

        db.add(NpdStep(
            request_id=req.id, step_code=code, status=step_status,
            sort_order=sd.sort_order, completed_at=completed_at,
            completed_by_id=completed_by_id,
        ))

    db.flush()
    return req


# ---------------------------------------------------------------------------
# Main seed function
# ---------------------------------------------------------------------------

def seed_demo_data(db: Session) -> dict:
    if db.query(SchemaMeta).filter(SchemaMeta.key == DEMO_KEY).first():
        return {"status": "already_loaded", "message": "Demo data already loaded."}

    # ---- Users ----
    lachie = _get_or_create_user(db, "lachie@demo.local", "Lachie Hodges", "editor")
    fraser = _get_or_create_user(db, "fraser@demo.local", "Fraser Smith", "editor")
    sarah = _get_or_create_user(db, "sarah@demo.local", "Sarah Chen", "viewer")

    # ---- Plants ----
    _ensure_plant(db, "QF00", "factory", "Rocklea Factory")
    _ensure_plant(db, "QW00", "warehouse", "Queensland Warehouse")
    _ensure_plant(db, "VW00", "warehouse", "Victoria Warehouse")
    _ensure_plant(db, "NW00", "warehouse", "NSW Warehouse")
    _ensure_plant(db, "TW00", "warehouse", "Tasmania Warehouse")

    # ---- Tags ----
    for code, label, color in [
        ("priority", "Priority", "#ef4444"),
        ("sap-review", "SAP Review", "#f59e0b"),
        ("costing-hold", "Costing Hold", "#8b5cf6"),
        ("new-range", "New Range", "#10b981"),
    ]:
        if not db.query(Tag).filter(Tag.code == code).first():
            db.add(Tag(code=code, label=label, color=color, display_order=0))
    db.flush()

    # ---- Preset field configuration ----
    # FG Factory preset (QF00)
    fg_fac = db.query(MaterialPreset).filter(MaterialPreset.preset_code == "fg_factory").first()
    bulk_pre = db.query(MaterialPreset).filter(MaterialPreset.preset_code == "bulk").first()
    fg_wh = db.query(MaterialPreset).filter(MaterialPreset.preset_code == "fg_warehouse").first()

    def _assign_plant(preset: MaterialPreset, plant_code: str) -> None:
        exists = (
            db.query(PresetPlant)
            .filter(PresetPlant.preset_id == preset.id, PresetPlant.plant_code == plant_code)
            .first()
        )
        if not exists:
            db.add(PresetPlant(preset_id=preset.id, plant_code=plant_code))

    def _add_field(
        preset: MaterialPreset, field_name: str, label: str, allowed: list[str],
        is_critical: bool = True, severity: str = "error",
        desc: str = "", impact: str = "", example: str = "",
    ) -> None:
        exists = (
            db.query(PresetField)
            .filter(PresetField.preset_id == preset.id, PresetField.field_name == field_name)
            .first()
        )
        if not exists:
            db.add(PresetField(
                preset_id=preset.id, field_name=field_name.upper(), label=label,
                is_critical=is_critical, allowed_values=json.dumps(allowed),
                severity=severity, sort_order=0,
                sap_description=desc, sap_impact=impact, sap_example=example,
            ))

    if fg_fac:
        _assign_plant(fg_fac, "QF00")
        _add_field(fg_fac, "DISMM", "MRP Type", ["PD", "MK"],
            desc="Defines the planning procedure (MRP, reorder point, etc).",
            impact="Wrong MRP type causes incorrect replenishment logic and over/under-production.",
            example="PD = MRP (Make-to-Stock). MK = MRP with forecast.")
        _add_field(fg_fac, "DISPO", "MRP Controller", ["100", "200", "300"],
            desc="The planning group responsible for this material.",
            impact="Wrong controller means the wrong planner owns the replenishment.",
            example="100 = Factory Planning, 200 = Scheduling, 300 = Imports")
        _add_field(fg_fac, "STRGR", "Strategy Group", ["40", "50"],
            desc="Determines how production orders are planned (make-to-stock vs make-to-order).",
            impact="Wrong strategy causes sales orders or forecasts to be consumed incorrectly.",
            example="40 = Make-to-Stock planning strategy.")
        _add_field(fg_fac, "BESKZ", "Procurement Type", ["E", "X"],
            is_critical=False, severity="warning",
            desc="Defines whether the material is produced in-house (E) or externally (F) or both (X).",
            impact="Incorrect procurement type stops production or purchase orders from being raised.",
            example="E = In-house production (manufactured at factory).")

    if bulk_pre:
        _assign_plant(bulk_pre, "QF00")
        _add_field(bulk_pre, "DISMM", "MRP Type", ["PD", "MK"],
            desc="Defines the planning procedure for this bulk intermediate.",
            impact="Wrong MRP type causes incorrect bulk replenishment.",
            example="PD = MRP-based replenishment.")
        _add_field(bulk_pre, "DISPO", "MRP Controller", ["100", "200"],
            desc="The planning group responsible for bulk scheduling.")

    if fg_wh:
        for wh in ["QW00", "VW00", "NW00", "TW00"]:
            _assign_plant(fg_wh, wh)
        _add_field(fg_wh, "DISMM", "MRP Type", ["ND", "MR"],
            desc="Warehouse materials should use ND (no planning) or MR (reorder-point).",
            impact="PD on a warehouse plant triggers unnecessary MRP runs.",
            example="ND = No MRP / consumption-driven replenishment.")

    db.flush()

    # Sync preset fields into GovernanceRule rows before creating MARC/violations
    preset_index = load_presets(db)
    sync_preset_fields_to_rules(db, preset_index)
    db.flush()

    # ---- Materials (MARA) ----
    # Bulk intermediates
    _make_material(db, "FD278068-B",  "HALB", "Bulk Base Coat FD278068",     "P001")
    _make_material(db, "194X0560-B",  "HALB", "Bulk Intermediate 194X0560",  "P001")
    _make_material(db, "51RD0059-B",  "HALB", "Bulk Red Oxide 51RD0059",     "P002")
    _make_material(db, "84LG0083-B",  "HALB", "Bulk Protective Grey 84LG",   "P003")
    _make_material(db, "84LG0187-B",  "HALB", "Bulk Legacy Grey 84LG0187",   "P003")
    _make_material(db, "80962005-B",  "HALB", "Bulk Primer 80962005",        "P001")
    _make_material(db, "403G059G-B",  "HALB", "Bulk Avista Green 403G059G",  "P004")
    _make_material(db, "403G057G-B",  "HALB", "Bulk Avista Gloss 403G057G",  "P004")
    _make_material(db, "48850077-B",  "HALB", "Bulk Top Coat 48850077",      "P003")
    _make_material(db, "97684892-B",  "HALB", "Bulk Epoxy 97684892",         "P001")
    _make_material(db, "731H0475-B",  "HALB", "Bulk Clearcoat 731H0475",     "P001")

    # Finished goods
    _make_material(db, "FD278068-15L",  "FERT", "Base Coat FD278068 15L",       "P001")
    _make_material(db, "194X0560-15L",  "FERT", "Intermediate 194X0560 15L",    "P001")
    _make_material(db, "51RD0059-10L",  "FERT", "Red Oxide 51RD0059 10L",       "P002")
    _make_material(db, "84LG0083-180L", "FERT", "Protective Grey 84LG0083 180L","P003")
    _make_material(db, "84LG0187-180L", "FERT", "Legacy Grey 84LG0187 180L",    "P003")
    _make_material(db, "80962005-15L",  "FERT", "Primer 80962005 15L",          "P001")
    _make_material(db, "403G059G-4L",   "FERT", "Avista Green 403G059G 4L",     "P004")
    _make_material(db, "403G057G-4L",   "FERT", "Avista Gloss 403G057G 4L",     "P004")
    _make_material(db, "48850077-4L",   "FERT", "Top Coat 48850077 4L",         "P003")
    _make_material(db, "97684892-3L",   "FERT", "Epoxy 97684892 3L",            "P001")
    _make_material(db, "731H0475-10L",  "FERT", "Clearcoat 731H0475 10L",       "P001")
    _make_material(db, "RBSRW057-4L",   "FERT", "Legacy Solvent 4L",            "P002")
    _make_material(db, "RBMRW057-4L",   "FERT", "Legacy Mineral 4L",            "P002")
    _make_material(db, "RBGRW057-4L",   "FERT", "Premium Gloss 4L",             "P001")

    # ---- MARC rows ----
    # Factory plant QF00 — bulk materials
    _make_marc(db, "FD278068-B",  "QF00", "A1", dismm="PD", dispo="100", strgr="40", beskz="E", dispr="MTSF")
    _make_marc(db, "194X0560-B",  "QF00", "N2", dismm="PD", dispo="100", strgr="40", beskz="E", dispr="MTSF")
    _make_marc(db, "51RD0059-B",  "QF00", "A1", dismm="PD", dispo="100", strgr="40", beskz="E", dispr="MTSF")
    _make_marc(db, "84LG0083-B",  "QF00", "A1", dismm="PD", dispo="200", strgr="40", beskz="E", dispr="MTSF")
    _make_marc(db, "84LG0187-B",  "QF00", "O1", dismm="PD", dispo="100", strgr="40", beskz="E", dispr="NOPL")
    _make_marc(db, "80962005-B",  "QF00", "A1", dismm="PD", dispo="100", strgr="40", beskz="E", dispr="MTSF")
    _make_marc(db, "403G059G-B",  "QF00", "N1", dismm="PD", dispo="100", strgr="40", beskz="E", dispr="MTSF")
    _make_marc(db, "403G057G-B",  "QF00", "A1", dismm="PD", dispo="200", strgr="40", beskz="E", dispr="MTSF")
    _make_marc(db, "48850077-B",  "QF00", "O2", dismm="PD", dispo="100", strgr="40", beskz="E", dispr="NOPL")
    _make_marc(db, "97684892-B",  "QF00", "N2", dismm="PD", dispo="100", strgr="40", beskz="E", dispr="MTSF")
    _make_marc(db, "731H0475-B",  "QF00", "A1", dismm="PD", dispo="100", strgr="40", beskz="E", dispr="MTSF")

    # Factory plant QF00 — FG materials (some with violations)
    _make_marc(db, "FD278068-15L",  "QF00", "A1", dismm="PD",  dispo="100", strgr="40", beskz="E", dispr="MTSF")
    _make_marc(db, "194X0560-15L",  "QF00", "N2", dismm="ND",  dispo="100", strgr="40", beskz="E", dispr="MTSF")   # VIOLATION: DISMM
    _make_marc(db, "51RD0059-10L",  "QF00", "A1", dismm="PD",  dispo="100", strgr="40", beskz="E", dispr="MTSF")
    _make_marc(db, "84LG0083-180L", "QF00", "A1", dismm="PD",  dispo="200", strgr="10", beskz="E", dispr="MTSF")   # VIOLATION: STRGR
    _make_marc(db, "84LG0187-180L", "QF00", "O1", dismm="PD",  dispo="100", strgr="40", beskz="E", dispr="NOPL")
    _make_marc(db, "80962005-15L",  "QF00", "A1", dismm="PD",  dispo="100", strgr="40", beskz="E", dispr="MTSF")
    _make_marc(db, "403G059G-4L",   "QF00", "N1", dismm="PD",  dispo="999", strgr="10", beskz="E", dispr="MTSF")   # VIOLATION: DISPO + STRGR
    _make_marc(db, "403G057G-4L",   "QF00", "A1", dismm="PD",  dispo="200", strgr="50", beskz="E", dispr="MTSF")
    _make_marc(db, "48850077-4L",   "QF00", "O2", dismm="PD",  dispo="100", strgr="40", beskz="E", dispr="NOPL")
    _make_marc(db, "97684892-3L",   "QF00", "N2", dismm="VB",  dispo="100", strgr="40", beskz="E", dispr="MTSF")   # VIOLATION: DISMM
    _make_marc(db, "731H0475-10L",  "QF00", "A1", dismm="PD",  dispo="100", strgr="40", beskz="E", dispr="MTSF")
    _make_marc(db, "RBSRW057-4L",   "QF00", "O3", dismm="PD",  dispo="100", strgr="40", beskz="E", dispr="OBSO")
    _make_marc(db, "RBMRW057-4L",   "QF00", "O2", dismm="PD",  dispo="100", strgr="40", beskz="F", dispr="NOPL")   # VIOLATION: BESKZ (warning)
    _make_marc(db, "RBGRW057-4L",   "QF00", "A1", dismm="PD",  dispo="100", strgr="40", beskz="E", dispr="MTSF")

    # Warehouse QW00 — FG materials (ND = correct for warehouse)
    _make_marc(db, "FD278068-15L",  "QW00", "A1", dismm="ND", dispo="100", strgr="40", beskz="F", dispr="MTSW")
    _make_marc(db, "51RD0059-10L",  "QW00", "A1", dismm="ND", dispo="100", strgr="40", beskz="F", dispr="MTSW")
    _make_marc(db, "84LG0083-180L", "QW00", "A1", dismm="ND", dispo="100", strgr="40", beskz="F", dispr="MTSW")
    _make_marc(db, "84LG0187-180L", "QW00", "O1", dismm="ND", dispo="100", strgr="40", beskz="F", dispr="NOPL")
    _make_marc(db, "80962005-15L",  "QW00", "A1", dismm="ND", dispo="100", strgr="40", beskz="F", dispr="MTSW")
    _make_marc(db, "403G057G-4L",   "QW00", "A1", dismm="ND", dispo="100", strgr="40", beskz="F", dispr="MTSW")
    _make_marc(db, "731H0475-10L",  "QW00", "A1", dismm="ND", dispo="100", strgr="40", beskz="F", dispr="MTSW")
    _make_marc(db, "RBSRW057-4L",   "QW00", "O3", dismm="ND", dispo="100", strgr="40", beskz="F", dispr="OBSO")
    _make_marc(db, "RBGRW057-4L",   "QW00", "A1", dismm="ND", dispo="100", strgr="40", beskz="F", dispr="MTSW")

    # Warehouse VW00
    _make_marc(db, "FD278068-15L",  "VW00", "A1", dismm="ND", dispo="100", strgr="40", beskz="F", dispr="MTSW")
    _make_marc(db, "51RD0059-10L",  "VW00", "A1", dismm="PD", dispo="100", strgr="40", beskz="F", dispr="MTSW")   # VIOLATION: warehouse DISMM
    _make_marc(db, "84LG0083-180L", "VW00", "A1", dismm="ND", dispo="100", strgr="40", beskz="F", dispr="MTSW")
    _make_marc(db, "731H0475-10L",  "VW00", "A1", dismm="ND", dispo="100", strgr="40", beskz="F", dispr="MTSW")
    _make_marc(db, "403G057G-4L",   "VW00", "A1", dismm="ND", dispo="100", strgr="40", beskz="F", dispr="MTSW")
    _make_marc(db, "RBGRW057-4L",   "VW00", "A1", dismm="ND", dispo="100", strgr="40", beskz="F", dispr="MTSW")

    db.flush()

    # ---- Update MarcFieldStats ----
    all_marc = list(db.scalars(select(Marc)).all())
    counts: dict[tuple[str, str], int] = {}
    for marc in all_marc:
        for field_attr in ["dismm", "dispo", "strgr", "beskz", "dispr", "mmsta"]:
            val = getattr(marc, field_attr, None)
            if val:
                key = (field_attr.upper(), str(val))
                counts[key] = counts.get(key, 0) + 1
    for (field_name, value), cnt in counts.items():
        existing = db.get(MarcFieldStats, (field_name, value))
        if existing:
            existing.seen_count = cnt
            existing.last_seen_at = _NOW
        else:
            db.add(MarcFieldStats(field_name=field_name, value=value, seen_count=cnt, last_seen_at=_NOW))
    db.flush()

    # ---- Products (direct creation, mirroring MARC data) ----
    # Factory QF00
    _make_product(db, "FD278068-B",  "QF00", "A1", "MTSF", 14, lachie)
    _make_product(db, "194X0560-B",  "QF00", "N2", "MTSF", 45, lachie)
    _make_product(db, "51RD0059-B",  "QF00", "A1", "MTSF", 22, fraser)
    _make_product(db, "84LG0083-B",  "QF00", "A1", "MTSF", 10, fraser)
    _make_product(db, "84LG0187-B",  "QF00", "O1", "NOPL", 31, lachie)
    _make_product(db, "80962005-B",  "QF00", "A1", "MTSF", 8,  fraser)
    _make_product(db, "403G059G-B",  "QF00", "N1", "MTSF", 6,  lachie)
    _make_product(db, "403G057G-B",  "QF00", "A1", "MTSF", 19, fraser)
    _make_product(db, "48850077-B",  "QF00", "O2", "NOPL", 55, lachie)
    _make_product(db, "97684892-B",  "QF00", "N2", "MTSF", 38, lachie)
    _make_product(db, "731H0475-B",  "QF00", "A1", "MTSF", 28, fraser)

    _make_product(db, "FD278068-15L",  "QF00", "A1", "MTSF",  14, lachie)
    _make_product(db, "194X0560-15L",  "QF00", "N2", "MTSF",  45, lachie, mrp_mismatch=True)
    _make_product(db, "51RD0059-10L",  "QF00", "A1", "MTSF",  22, fraser)
    _make_product(db, "84LG0083-180L", "QF00", "A1", "MTSF",  10, fraser, mrp_mismatch=True)
    _make_product(db, "84LG0187-180L", "QF00", "O1", "NOPL",  31, lachie)
    _make_product(db, "80962005-15L",  "QF00", "A1", "MTSF",  8,  fraser)
    _make_product(db, "403G059G-4L",   "QF00", "N1", "MTSF",  6,  lachie, mrp_mismatch=True)
    _make_product(db, "403G057G-4L",   "QF00", "A1", "MTSF",  19, fraser)
    _make_product(db, "48850077-4L",   "QF00", "O2", "NOPL",  55, lachie)
    _make_product(db, "97684892-3L",   "QF00", "N2", "MTSF",  38, lachie, mrp_mismatch=True)
    _make_product(db, "731H0475-10L",  "QF00", "A1", "MTSF",  28, fraser)
    _make_product(db, "RBSRW057-4L",   "QF00", "O3", "OBSO",  90, lachie)
    _make_product(db, "RBMRW057-4L",   "QF00", "O2", "NOPL",  62, lachie, mrp_mismatch=True)
    _make_product(db, "RBGRW057-4L",   "QF00", "A1", "MTSF",  17, fraser)

    # Warehouses
    _make_product(db, "FD278068-15L",  "QW00", "A1", "MTSW", 14)
    _make_product(db, "51RD0059-10L",  "QW00", "A1", "MTSW", 22)
    _make_product(db, "84LG0083-180L", "QW00", "A1", "MTSW", 10)
    _make_product(db, "84LG0187-180L", "QW00", "O1", "NOPL", 31)
    _make_product(db, "80962005-15L",  "QW00", "A1", "MTSW", 8)
    _make_product(db, "403G057G-4L",   "QW00", "A1", "MTSW", 19)
    _make_product(db, "731H0475-10L",  "QW00", "A1", "MTSW", 28)
    _make_product(db, "RBSRW057-4L",   "QW00", "O3", "OBSO", 90)
    _make_product(db, "RBGRW057-4L",   "QW00", "A1", "MTSW", 17)

    _make_product(db, "FD278068-15L",  "VW00", "A1", "MTSW", 14)
    _make_product(db, "51RD0059-10L",  "VW00", "A1", "MTSW", 22, mrp_mismatch=True)
    _make_product(db, "84LG0083-180L", "VW00", "A1", "MTSW", 10)
    _make_product(db, "731H0475-10L",  "VW00", "A1", "MTSW", 28)
    _make_product(db, "403G057G-4L",   "VW00", "A1", "MTSW", 19)
    _make_product(db, "RBGRW057-4L",   "VW00", "A1", "MTSW", 17)

    db.flush()

    # ---- Rebuild violations from preset rules ----
    rule_index_fresh = load_presets(db)
    sync_preset_fields_to_rules(db, rule_index_fresh)
    db.flush()
    rebuild_violations(db)
    db.flush()

    # ---- NPD Pipeline requests ----
    ALL_STEPS = [
        "warehouse_ext", "bulk_master_data", "fg_master_data", "fg_routings",
        "fg_warehouse_ext", "costings", "ebr_ready", "master_data_check",
        "batch_raised", "batch_scheduled",
    ]

    # 1. COMPLETED — 731H0475 series
    req1 = _make_npd(
        db, "NPD-2026-001", "bulk_fg", "product_vision", "54",
        "731H0475-B", "731H0475-10L", ["QW00", "VW00"],
        _date_ago(5), fraser, "completed", 42,
        steps_completed=ALL_STEPS,
        notes="Clearcoat extension — Product Vision initiative Q1 2026.",
    )

    # 2. IN PROGRESS step 7 — FD278068 series
    req2 = _make_npd(
        db, "NPD-2026-002", "bulk_fg", "planning", "54",
        "FD278068-B", "FD278068-15L", ["QW00", "VW00", "NW00"],
        _date_ago(10), lachie, "in_progress", 28,
        steps_completed=[
            "warehouse_ext", "bulk_master_data", "fg_master_data",
            "fg_routings", "fg_warehouse_ext", "costings",
        ],
        notes="National rollout — Base Coat extension to all warehouses.",
    )

    # 3. IN PROGRESS step 4 — 84LG0083 series
    req3 = _make_npd(
        db, "NPD-2026-003", "bulk_fg", "planning", "55",
        "84LG0083-B", "84LG0083-180L", ["QW00", "VW00"],
        _date_ago(20), lachie, "in_progress", 18,
        steps_completed=["warehouse_ext", "bulk_master_data", "fg_master_data"],
        notes="Protective Coatings new drum size — 180L bulk format.",
    )

    # 4. IN PROGRESS step 2 — 97684892 series
    req4 = _make_npd(
        db, "NPD-2026-004", "bulk_fg", "execution_release", "54",
        "97684892-B", "97684892-3L", ["QW00"],
        _date_ago(30), lachie, "in_progress", 14,
        steps_completed=["warehouse_ext"],
        notes="Epoxy 3L pack — Execution Release from S4.",
    )

    # 5. ON HOLD — 403G059G series
    req5 = _make_npd(
        db, "NPD-2026-005", "bulk_fg", "product_vision", "75",
        "403G059G-B", "403G059G-4L", ["QW00", "VW00"],
        _date_ago(45), lachie, "on_hold", 21,
        steps_completed=["warehouse_ext", "bulk_master_data"],
        notes="Avista Green — on hold pending formulation sign-off.",
    )

    db.flush()

    # ---- NPD Comments ----
    def _add_npd_comment(req: NpdRequest, user: User, body: str, days_ago: int) -> None:
        db.add(NpdComment(
            request_id=req.id, user_id=user.id, body=body,
            created_at=_ago(days_ago),
        ))

    _add_npd_comment(req1, fraser, "All steps complete — batch 10126280 scheduled for 22/08/2025.", 5)
    _add_npd_comment(req2, lachie, "Warehouse extension to VW00 and NW00 confirmed. Proceeding to bulk master data.", 25)
    _add_npd_comment(req2, fraser, "EBR approval received from P&C. Costings signed off — raising batch next week.", 8)
    _add_npd_comment(req3, lachie, "Costings delayed — awaiting raw material price update from procurement.", 12)
    _add_npd_comment(req3, sarah, "Finance have confirmed pricing. Costings should be completed by end of week.", 5)
    _add_npd_comment(req4, lachie, "Warehouse extension raised in SAP. Bulk master data in progress.", 10)
    _add_npd_comment(req5, lachie, "On hold pending formulation sign-off from R&D. Expected to resume in 2 weeks.", 18)

    # ---- NPD Email events ----
    db.add(NpdEmailEvent(
        request_id=req2.id,
        received_at=_ago(8),
        sender="noreply@planner.local",
        subject="FD278068-15L — Costings Complete",
        body_snippet="Hi team, costings for FD278068-15L are now complete and approved in the system.",
        matched_step_code="costings",
        matched_status="completed",
        applied=True,
        source="manual_paste",
        raw_payload="{}",
    ))
    db.add(NpdEmailEvent(
        request_id=None,
        received_at=_ago(3),
        sender="noreply@mslists.local",
        subject="84LG0083-180L — Routings Setup",
        body_snippet="Routings for 84LG0083-180L have been configured in PP module.",
        matched_step_code=None,
        matched_status=None,
        applied=False,
        source="manual_paste",
        raw_payload="{}",
    ))

    db.flush()
    db.add(SchemaMeta(key=DEMO_KEY, value="applied"))

    return {
        "status": "loaded",
        "message": (
            "Demo data loaded: 25 materials, 40 products across QF00/QW00/VW00, "
            "governance violations, 7 presets configured, 5 NPD requests."
        ),
    }


def reset_demo_data(db: Session) -> None:
    """Remove the schema_meta guard so demo can be re-seeded."""
    db.query(SchemaMeta).filter(SchemaMeta.key == DEMO_KEY).delete()
    db.flush()
