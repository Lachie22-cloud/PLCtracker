"""Obsoletion review page: everything in O1/O2 with inline notes + next review date.

Designed for the monthly obsoletion meeting. Each row is a product at a single
plant; you can edit the review date, review note, and owner inline without
leaving the page.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_user
from ..db import get_db
from ..models import (
    Comment,
    LifecycleStage,
    Plant,
    Product,
    StageTransition,
    Tag,
    User,
)
from ..templating import templates

router = APIRouter()


@router.get("/review")
async def review_board(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    stage: List[str] = Query(default=["O1", "O2"]),
    owner: List[int] = Query(default=[]),
    overdue_only: Optional[str] = None,
):
    q = (
        select(Product)
        .where(Product.stage_code.in_(stage))
        .order_by(Product.next_review_date, Product.stage_code, Product.material_no)
    )
    if owner:
        q = q.where(Product.owner_id.in_(owner))
    products = list(db.scalars(q).all())

    # Latest comment per product (for hint column)
    product_ids = [p.id for p in products]
    latest_comments: dict[int, Comment] = {}
    if product_ids:
        for c in db.scalars(
            select(Comment)
            .where(Comment.product_id.in_(product_ids))
            .order_by(Comment.created_at.desc())
        ).all():
            latest_comments.setdefault(c.product_id, c)

    # Last transition per product
    last_trans: dict[int, StageTransition] = {}
    if product_ids:
        for t in db.scalars(
            select(StageTransition)
            .where(StageTransition.product_id.in_(product_ids))
            .order_by(StageTransition.detected_at.desc())
        ).all():
            last_trans.setdefault(t.product_id, t)

    now = datetime.utcnow()
    today = now.date()

    def _is_overdue(p: Product) -> bool:
        return p.next_review_date is not None and p.next_review_date.date() <= today

    if overdue_only:
        products = [p for p in products if _is_overdue(p)]

    all_stages = list(
        db.scalars(select(LifecycleStage).order_by(LifecycleStage.display_order)).all()
    )
    all_users = list(db.scalars(select(User).order_by(User.name)).all())
    all_plants = list(db.scalars(select(Plant).order_by(Plant.plant_code)).all())
    all_tags = list(db.scalars(select(Tag).order_by(Tag.display_order)).all())

    total = len(products)
    overdue_count = sum(1 for p in products if _is_overdue(p))
    no_review = sum(1 for p in products if p.next_review_date is None)
    unassigned = sum(1 for p in products if p.owner_id is None)

    return templates.TemplateResponse(
        "review.html",
        {
            "request": request,
            "user": user,
            "products": products,
            "latest_comments": latest_comments,
            "last_trans": last_trans,
            "all_stages": all_stages,
            "all_users": all_users,
            "all_plants": all_plants,
            "all_tags": all_tags,
            "selected_stages": stage,
            "selected_owners": owner,
            "overdue_only": bool(overdue_only),
            "total": total,
            "overdue_count": overdue_count,
            "no_review": no_review,
            "unassigned": unassigned,
            "today": today,
        },
    )


@router.post("/review/{product_id}/note")
async def review_inline_note(
    product_id: int,
    next_review_date: str = Form(""),
    review_note: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404)
    if next_review_date.strip():
        try:
            product.next_review_date = datetime.fromisoformat(next_review_date)
        except ValueError:
            product.next_review_date = None
    else:
        product.next_review_date = None

    # If review_note is different from existing, also append to comments so
    # it's part of the permanent record (the single review_note slot is a
    # "current summary").
    new_note = review_note.strip()
    if new_note and new_note != (product.review_note or "").strip():
        db.add(
            Comment(
                product_id=product_id,
                user_id=user.id,
                body=f"[review] {new_note}",
            )
        )
    product.review_note = new_note
    db.commit()
    return RedirectResponse(url="/review", status_code=303)


@router.post("/review/{product_id}/owner")
async def review_inline_owner(
    product_id: int,
    owner_id: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404)
    product.owner_id = int(owner_id) if owner_id else None
    db.commit()
    return RedirectResponse(url="/review", status_code=303)


@router.post("/review/{product_id}/stage")
async def review_inline_stage(
    product_id: int,
    stage_code: str = Form(...),
    rationale: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """Advance stage straight from the review page (e.g. O1 -> O2)."""
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404)
    new_code = stage_code.strip().upper()
    if db.query(LifecycleStage).filter(LifecycleStage.code == new_code).first() is None:
        raise HTTPException(status_code=400, detail="Unknown stage")
    if product.stage_code != new_code:
        now = datetime.utcnow()
        db.add(
            StageTransition(
                product_id=product_id,
                from_stage_code=product.stage_code,
                to_stage_code=new_code,
                from_snapshot_id=None,
                to_snapshot_id=None,
                detected_at=now,
                rationale=rationale.strip(),
                changed_by_id=user.id,
            )
        )
        product.stage_code = new_code
        product.stage_since = now
        db.commit()
        from ..services.snapshot import _recompute_family_mismatches
        _recompute_family_mismatches(db)
        db.commit()
    return RedirectResponse(url="/review", status_code=303)
