"""Board, table, product-detail routes."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_user
from ..db import get_db
from ..models import (
    Action,
    Comment,
    LifecycleStage,
    Plant,
    Product,
    StageTransition,
    User,
)
from ..templating import templates

router = APIRouter()


def _apply_filters(
    query,
    *,
    plants: Optional[List[str]] = None,
    material: Optional[str] = None,
    stages: Optional[List[str]] = None,
    owners: Optional[List[int]] = None,
):
    if plants:
        query = query.where(Product.plant_code.in_(plants))
    if stages:
        query = query.where(Product.stage_code.in_(stages))
    if owners:
        query = query.where(Product.owner_id.in_(owners))
    if material:
        query = query.where(Product.material_no.contains(material))
    return query


def _filter_context(db: Session) -> dict:
    stages = list(
        db.scalars(select(LifecycleStage).order_by(LifecycleStage.display_order)).all()
    )
    plants = list(db.scalars(select(Plant).order_by(Plant.plant_code)).all())
    owners = list(db.scalars(select(User).order_by(User.name)).all())
    return {"all_stages": stages, "all_plants": plants, "all_owners": owners}


@router.get("/board")
async def board(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    plant: Optional[List[str]] = None,
    material: Optional[str] = None,
    owner: Optional[List[int]] = None,
):
    ctx = _filter_context(db)
    q = select(Product)
    q = _apply_filters(q, plants=plant, material=material, owners=owner)
    products = list(db.scalars(q).all())

    by_stage: dict[str, list[Product]] = {s.code: [] for s in ctx["all_stages"]}
    for p in products:
        by_stage.setdefault(p.stage_code, []).append(p)

    return templates.TemplateResponse(
        "board.html",
        {
            "request": request,
            "user": user,
            **ctx,
            "by_stage": by_stage,
            "selected_plants": plant or [],
            "selected_material": material or "",
            "selected_owners": owner or [],
        },
    )


@router.get("/products")
async def products_table(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    plant: Optional[List[str]] = None,
    material: Optional[str] = None,
    stage: Optional[List[str]] = None,
    owner: Optional[List[int]] = None,
    mismatch: Optional[str] = None,
):
    ctx = _filter_context(db)
    q = select(Product).order_by(Product.material_no, Product.plant_code)
    q = _apply_filters(q, plants=plant, material=material, stages=stage, owners=owner)
    if mismatch == "mrp":
        q = q.where(Product.mrp_mismatch.is_(True))
    elif mismatch == "family":
        q = q.where(Product.family_mismatch.is_(True))
    products = list(db.scalars(q).all())

    return templates.TemplateResponse(
        "products.html",
        {
            "request": request,
            "user": user,
            **ctx,
            "products": products,
            "selected_plants": plant or [],
            "selected_material": material or "",
            "selected_stages": stage or [],
            "selected_owners": owner or [],
            "mismatch": mismatch or "",
        },
    )


@router.get("/products/{product_id}")
async def product_detail(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404)

    comments = list(
        db.scalars(
            select(Comment)
            .where(Comment.product_id == product_id)
            .order_by(Comment.created_at.desc())
        ).all()
    )
    actions = list(
        db.scalars(
            select(Action)
            .where(Action.product_id == product_id)
            .order_by(Action.status, Action.due_date)
        ).all()
    )
    transitions = list(
        db.scalars(
            select(StageTransition)
            .where(StageTransition.product_id == product_id)
            .order_by(StageTransition.detected_at.desc())
        ).all()
    )
    all_stages = list(
        db.scalars(select(LifecycleStage).order_by(LifecycleStage.display_order)).all()
    )
    all_users = list(db.scalars(select(User).order_by(User.name)).all())

    return templates.TemplateResponse(
        "product_detail.html",
        {
            "request": request,
            "user": user,
            "product": product,
            "comments": comments,
            "actions": actions,
            "transitions": transitions,
            "all_stages": all_stages,
            "all_users": all_users,
        },
    )


@router.post("/products/{product_id}/comment")
async def add_comment(
    product_id: int,
    body: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404)
    if body.strip():
        db.add(Comment(product_id=product_id, user_id=user.id, body=body.strip()))
        db.commit()
    return RedirectResponse(url=f"/products/{product_id}", status_code=303)


@router.post("/products/{product_id}/owner")
async def set_owner(
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
    return RedirectResponse(url=f"/products/{product_id}", status_code=303)


@router.post("/products/{product_id}/action")
async def create_action(
    product_id: int,
    title: str = Form(...),
    due_date: str = Form(""),
    assignee_id: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404)
    from datetime import datetime

    due_dt = None
    if due_date:
        try:
            due_dt = datetime.fromisoformat(due_date)
        except ValueError:
            due_dt = None

    db.add(
        Action(
            product_id=product_id,
            created_by_id=user.id,
            assignee_id=int(assignee_id) if assignee_id else None,
            title=title.strip(),
            due_date=due_dt,
            status="open",
        )
    )
    db.commit()
    return RedirectResponse(url=f"/products/{product_id}", status_code=303)


@router.post("/actions/{action_id}/complete")
async def complete_action(
    action_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    from datetime import datetime

    action = db.get(Action, action_id)
    if action is None:
        raise HTTPException(status_code=404)
    action.status = "done"
    action.completed_at = datetime.utcnow()
    db.commit()
    return RedirectResponse(url=f"/products/{action.product_id}", status_code=303)
