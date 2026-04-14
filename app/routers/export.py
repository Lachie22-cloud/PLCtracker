"""CSV export of the (filtered) product list."""
from __future__ import annotations

import csv
import io
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_user
from ..db import get_db
from ..models import Product, User

router = APIRouter()


@router.get("/export.csv")
async def export_csv(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    plant: List[str] = Query(default=[]),
    material: Optional[str] = None,
    stage: List[str] = Query(default=[]),
    owner: List[int] = Query(default=[]),
    mismatch: Optional[str] = None,
):
    q = select(Product).order_by(Product.material_no, Product.plant_code)
    if plant:
        q = q.where(Product.plant_code.in_(plant))
    if stage:
        q = q.where(Product.stage_code.in_(stage))
    if owner:
        q = q.where(Product.owner_id.in_(owner))
    if material:
        q = q.where(Product.material_no.contains(material))
    if mismatch == "mrp":
        q = q.where(Product.mrp_mismatch.is_(True))
    elif mismatch == "family":
        q = q.where(Product.family_mismatch.is_(True))

    products = list(db.scalars(q).all())

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "Material",
            "Plant",
            "Stage",
            "MRP profile",
            "MRP mismatch",
            "MRP note",
            "Family mismatch",
            "Family note",
            "Owner",
            "First seen",
            "Last seen",
            "Days in stage",
        ]
    )
    from datetime import datetime

    now = datetime.utcnow()
    for p in products:
        owner_name = p.owner.name if p.owner else ""
        days = (now - p.stage_since).days if p.stage_since else 0
        writer.writerow(
            [
                p.material_no,
                p.plant_code,
                p.stage_code,
                p.mrp_profile,
                "Y" if p.mrp_mismatch else "",
                p.mrp_mismatch_note,
                "Y" if p.family_mismatch else "",
                p.family_mismatch_note,
                owner_name,
                p.first_seen_at.isoformat() if p.first_seen_at else "",
                p.last_seen_at.isoformat() if p.last_seen_at else "",
                days,
            ]
        )

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="plctracker-export.csv"'},
    )
