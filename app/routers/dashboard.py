"""Dashboard: counts per stage, aging, transitions, mismatches."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import require_user
from ..db import get_db
from ..models import (
    LifecycleStage,
    Plant,
    Product,
    StageTransition,
    User,
)
from ..templating import templates

router = APIRouter()


@router.get("/dashboard")
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    plant: Optional[List[str]] = None,
    material: Optional[str] = None,
    owner: Optional[List[int]] = None,
):
    stages = list(
        db.scalars(select(LifecycleStage).order_by(LifecycleStage.display_order)).all()
    )
    all_plants = list(db.scalars(select(Plant).order_by(Plant.plant_code)).all())
    all_users = list(db.scalars(select(User).order_by(User.name)).all())

    q = select(Product)
    if plant:
        q = q.where(Product.plant_code.in_(plant))
    if owner:
        q = q.where(Product.owner_id.in_(owner))
    if material:
        q = q.where(Product.material_no.contains(material))
    products = list(db.scalars(q).all())

    # Count per stage
    counts = {s.code: 0 for s in stages}
    for p in products:
        counts[p.stage_code] = counts.get(p.stage_code, 0) + 1

    # Aging (days in current stage) histogram — buckets: 0-7, 8-30, 31-90, 90+
    now = datetime.utcnow()
    aging_buckets = {"0-7": 0, "8-30": 0, "31-90": 0, "90+": 0}
    for p in products:
        if p.stage_since is None:
            continue
        days = (now - p.stage_since).days
        if days <= 7:
            aging_buckets["0-7"] += 1
        elif days <= 30:
            aging_buckets["8-30"] += 1
        elif days <= 90:
            aging_buckets["31-90"] += 1
        else:
            aging_buckets["90+"] += 1

    mrp_mismatch_count = sum(1 for p in products if p.mrp_mismatch)
    family_mismatch_count = sum(1 for p in products if p.family_mismatch)

    # Recent transitions (last 90 days, matching filters)
    since = now - timedelta(days=90)
    product_ids = {p.id for p in products}
    t_q = select(StageTransition).where(StageTransition.detected_at >= since)
    transitions = [
        t for t in db.scalars(t_q).all() if not product_ids or t.product_id in product_ids
    ]
    transitions.sort(key=lambda t: t.detected_at, reverse=True)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "all_stages": stages,
            "all_plants": all_plants,
            "all_owners": all_users,
            "counts": counts,
            "aging": aging_buckets,
            "mrp_mismatch_count": mrp_mismatch_count,
            "family_mismatch_count": family_mismatch_count,
            "total_products": len(products),
            "transitions": transitions[:50],
            "selected_plants": plant or [],
            "selected_material": material or "",
            "selected_owners": owner or [],
        },
    )
