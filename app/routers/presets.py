"""Presets: admin-configurable MARC field expectation presets."""
from __future__ import annotations

import json
from typing import List

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_admin, require_user
from ..db import get_db
from ..models import (
    MarcFieldStats,
    MaterialPreset,
    Plant,
    PresetField,
    PresetPlant,
    User,
)
from ..templating import templates

router = APIRouter()

MARC_FIELDS_LABELS = {
    "dismm": "MRP Type",
    "dispo": "MRP Controller",
    "strgr": "Strategy Group",
    "losfx": "Fixed Lot Size",
    "eisbe": "Safety Stock",
    "minbe": "Reorder Point",
    "beskz": "Procurement Type",
    "sobsl": "Special Procurement",
    "ekgrp": "Purchasing Group",
    "disgr": "MRP Group",
    "dispr": "MRP Profile",
    "plifz": "Planned Delivery Time",
    "webaz": "GR Processing Time",
    "lgpro": "Issue Storage Location",
    "lgfsb": "External Procurement SL",
    "fhori": "Scheduling Margin Key",
    "schgt": "Bulk Material Indicator",
    "perkz": "Period Indicator",
    "mtvfp": "Availability Check",
    "mmsta": "Plant-Specific Material Status",
}


def _get_preset_or_404(db: Session, code: str) -> MaterialPreset:
    preset = db.query(MaterialPreset).filter(MaterialPreset.preset_code == code).first()
    if preset is None:
        raise HTTPException(status_code=404, detail="Preset not found")
    return preset


@router.get("/presets")
async def presets_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    presets = list(
        db.scalars(select(MaterialPreset).order_by(MaterialPreset.display_order)).all()
    )
    return templates.TemplateResponse(
        "presets_list.html",
        {
            "request": request,
            "user": user,
            "presets": presets,
        },
    )


@router.get("/presets/new")
async def preset_new_form(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    all_plants = list(db.scalars(select(Plant).order_by(Plant.plant_code)).all())
    return templates.TemplateResponse(
        "preset_edit.html",
        {
            "request": request,
            "user": user,
            "preset": None,
            "all_plants": all_plants,
            "marc_fields": MARC_FIELDS_LABELS,
        },
    )


@router.post("/presets/new")
async def preset_create(
    request: Request,
    preset_code: str = Form(...),
    label: str = Form(...),
    description: str = Form(""),
    display_order: int = Form(0),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    preset_code = preset_code.strip().lower().replace(" ", "_")
    if db.query(MaterialPreset).filter(MaterialPreset.preset_code == preset_code).first():
        raise HTTPException(status_code=400, detail="Preset code already exists")
    preset = MaterialPreset(
        preset_code=preset_code,
        label=label.strip(),
        description=description.strip(),
        display_order=display_order,
    )
    db.add(preset)
    db.commit()
    return RedirectResponse(url=f"/presets/{preset_code}/edit", status_code=303)


@router.get("/presets/{code}/edit")
async def preset_edit_form(
    code: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    preset = _get_preset_or_404(db, code)
    all_plants = list(db.scalars(select(Plant).order_by(Plant.plant_code)).all())
    return templates.TemplateResponse(
        "preset_edit.html",
        {
            "request": request,
            "user": user,
            "preset": preset,
            "all_plants": all_plants,
            "marc_fields": MARC_FIELDS_LABELS,
        },
    )


@router.post("/presets/{code}/edit")
async def preset_save(
    code: str,
    label: str = Form(...),
    description: str = Form(""),
    display_order: int = Form(0),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    preset = _get_preset_or_404(db, code)
    preset.label = label.strip()
    preset.description = description.strip()
    preset.display_order = display_order
    db.commit()
    return RedirectResponse(url=f"/presets/{code}/edit", status_code=303)


@router.post("/presets/{code}/plants")
async def preset_save_plants(
    code: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    preset = _get_preset_or_404(db, code)
    form_data = await request.form()
    plant_codes: List[str] = form_data.getlist("plant_codes")  # type: ignore[assignment]

    # Remove all existing associations then re-add
    db.query(PresetPlant).filter(PresetPlant.preset_id == preset.id).delete(
        synchronize_session=False
    )
    for pc in plant_codes:
        db.add(PresetPlant(preset_id=preset.id, plant_code=pc))
    db.commit()
    return RedirectResponse(url=f"/presets/{code}/edit", status_code=303)


@router.post("/presets/{code}/fields")
async def preset_add_field(
    code: str,
    field_name: str = Form(...),
    label: str = Form(...),
    is_critical: str = Form(""),
    severity: str = Form("error"),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    preset = _get_preset_or_404(db, code)
    max_order = max((pf.sort_order for pf in preset.fields), default=-1) + 1
    pf = PresetField(
        preset_id=preset.id,
        field_name=field_name.strip().lower(),
        label=label.strip(),
        is_critical=bool(is_critical),
        severity=severity if severity in ("error", "warning", "info") else "error",
        sort_order=max_order,
    )
    db.add(pf)
    db.commit()
    return RedirectResponse(url=f"/presets/{code}/edit", status_code=303)


@router.post("/presets/{code}/fields/{field_id}/values")
async def preset_field_values(
    code: str,
    field_id: int,
    allowed_values_json: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    pf = db.get(PresetField, field_id)
    if pf is None:
        raise HTTPException(status_code=404)
    # Validate JSON
    try:
        vals = json.loads(allowed_values_json)
        if not isinstance(vals, list):
            raise ValueError
        pf.allowed_values = json.dumps([str(v).strip() for v in vals if str(v).strip()])
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="allowed_values_json must be a JSON array")
    db.commit()
    return RedirectResponse(url=f"/presets/{code}/edit", status_code=303)


@router.post("/presets/{code}/fields/{field_id}/delete")
async def preset_delete_field(
    code: str,
    field_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    pf = db.get(PresetField, field_id)
    if pf:
        db.delete(pf)
        db.commit()
    return RedirectResponse(url=f"/presets/{code}/edit", status_code=303)


@router.get("/presets/field-stats/{field_name}")
async def field_stats(
    field_name: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    rows = list(
        db.scalars(
            select(MarcFieldStats)
            .where(MarcFieldStats.field_name == field_name.upper())
            .order_by(MarcFieldStats.seen_count.desc())
        ).all()
    )
    return JSONResponse([{"value": r.value, "seen_count": r.seen_count} for r in rows])
