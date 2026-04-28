"""Admin: users, stages, plants, MRP rules, snapshot history."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import hash_password, require_admin
from ..db import get_db
from ..models import LifecycleStage, MrpRule, Plant, Snapshot, Tag, User
from ..services.demo_seed import reset_demo_data, seed_demo_data
from ..services.snapshot import _recompute_family_mismatches
from ..templating import templates

router = APIRouter()


@router.get("/admin")
async def admin_home(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    users = list(db.scalars(select(User).order_by(User.email)).all())
    stages = list(
        db.scalars(select(LifecycleStage).order_by(LifecycleStage.display_order)).all()
    )
    plants = list(db.scalars(select(Plant).order_by(Plant.plant_code)).all())
    rules = list(db.scalars(select(MrpRule)).all())
    # Build matrix[stage_code][plant_code or '*'] = profile
    matrix: dict[str, dict[str, str]] = {s.code: {} for s in stages}
    for r in rules:
        matrix.setdefault(r.stage_code, {})[r.plant_code or "*"] = r.expected_mrp_profile
    snapshots = list(
        db.scalars(select(Snapshot).order_by(Snapshot.uploaded_at.desc())).all()
    )[:50]
    tags = list(db.scalars(select(Tag).order_by(Tag.display_order)).all())
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "user": user,
            "users": users,
            "stages": stages,
            "plants": plants,
            "matrix": matrix,
            "snapshots": snapshots,
            "tags": tags,
        },
    )


# --- Users -----------------------------------------------------------------

@router.post("/admin/users")
async def create_user(
    email: str = Form(...),
    name: str = Form(""),
    password: str = Form(...),
    role: str = Form("editor"),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    email = email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    db.add(
        User(
            email=email,
            name=name.strip(),
            password_hash=hash_password(password),
            role=role if role in ("admin", "editor", "viewer") else "editor",
        )
    )
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/admin/users/{user_id}/password")
async def reset_password(
    user_id: int,
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404)
    target.password_hash = hash_password(new_password)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/admin/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404)
    target.is_active = not target.is_active
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


# --- Plants ----------------------------------------------------------------

@router.post("/admin/plants/{plant_code}")
async def update_plant(
    plant_code: str,
    plant_type: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    plant = db.get(Plant, plant_code)
    if not plant:
        plant = Plant(plant_code=plant_code)
        db.add(plant)
    if plant_type not in ("factory", "warehouse", "other"):
        plant_type = "warehouse"
    plant.plant_type = plant_type
    plant.description = description.strip()
    db.commit()
    # Type change affects family-mismatch -> recompute
    _recompute_family_mismatches(db)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


# --- Lifecycle stages ------------------------------------------------------

@router.post("/admin/stages/{stage_code}")
async def update_stage(
    stage_code: str,
    label: str = Form(...),
    family: str = Form("Other"),
    display_order: int = Form(0),
    color: str = Form("#888888"),
    is_terminal: str = Form(""),
    expected_days: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    stage = db.query(LifecycleStage).filter(LifecycleStage.code == stage_code).first()
    if not stage:
        stage = LifecycleStage(code=stage_code)
        db.add(stage)
    stage.label = label.strip()
    stage.family = family.strip() or "Other"
    stage.display_order = int(display_order)
    stage.color = color.strip()
    stage.is_terminal = bool(is_terminal)
    try:
        stage.expected_days = int(expected_days) if expected_days.strip() else None
    except ValueError:
        stage.expected_days = None
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


# --- Tags ------------------------------------------------------------------

@router.post("/admin/tags")
async def create_tag(
    code: str = Form(...),
    label: str = Form(...),
    color: str = Form("#64748b"),
    description: str = Form(""),
    display_order: int = Form(0),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    code = code.strip().lower()
    if db.query(Tag).filter(Tag.code == code).first():
        raise HTTPException(status_code=400, detail="Tag code already exists")
    db.add(
        Tag(
            code=code,
            label=label.strip(),
            color=color.strip(),
            description=description.strip(),
            display_order=int(display_order),
        )
    )
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/admin/tags/{tag_id}")
async def update_tag(
    tag_id: int,
    label: str = Form(...),
    color: str = Form("#64748b"),
    description: str = Form(""),
    display_order: int = Form(0),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    tag = db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404)
    tag.label = label.strip()
    tag.color = color.strip()
    tag.description = description.strip()
    tag.display_order = int(display_order)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/admin/tags/{tag_id}/delete")
async def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    tag = db.get(Tag, tag_id)
    if tag:
        db.delete(tag)
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)


# --- MRP rules -------------------------------------------------------------

@router.post("/admin/mrp_rules")
async def set_mrp_rule(
    stage_code: str = Form(...),
    plant_code: str = Form(""),
    expected_mrp_profile: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    plant_key = plant_code.strip() or None
    existing = (
        db.query(MrpRule)
        .filter(MrpRule.stage_code == stage_code, MrpRule.plant_code == plant_key)
        .first()
    )
    if expected_mrp_profile.strip() == "":
        if existing:
            db.delete(existing)
    else:
        if existing:
            existing.expected_mrp_profile = expected_mrp_profile.strip().upper()
        else:
            db.add(
                MrpRule(
                    stage_code=stage_code,
                    plant_code=plant_key,
                    expected_mrp_profile=expected_mrp_profile.strip().upper(),
                )
            )
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


# --- Demo data ---------------------------------------------------------------

@router.post("/admin/demo/load")
async def load_demo(
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    result = seed_demo_data(db)
    db.commit()
    msg = result["message"]
    return RedirectResponse(url=f"/admin?demo_msg={msg}", status_code=303)


@router.post("/admin/demo/reset")
async def reset_demo(
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    reset_demo_data(db)
    db.commit()
    return RedirectResponse(url="/admin?demo_msg=Demo+data+guard+cleared.+You+can+reload+now.", status_code=303)
