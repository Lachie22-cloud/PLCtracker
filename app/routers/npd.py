"""NPD Pipeline: new product development request tracker."""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_user
from ..db import get_db
from ..models import (
    NpdComment,
    NpdDivision,
    NpdEmailEvent,
    NpdRequest,
    NpdStep,
    NpdStepDefinition,
    User,
)
from ..services.npd_email import apply_email_event, parse_email
from ..templating import templates

router = APIRouter()

REQUEST_TYPES = [
    ("bulk_fg", "Bulk + FG"),
    ("fg_only", "FG Only"),
    ("bulk_only", "Bulk Only"),
]

REQUEST_FROM_CHOICES = [
    ("product_vision", "Product Vision"),
    ("planning", "Planning"),
    ("execution_release", "Execution / Release"),
    ("email", "Email"),
    ("new_sku", "New SKU"),
]


def _generate_request_no(db: Session) -> str:
    year = datetime.utcnow().year
    count = db.query(NpdRequest).filter(
        NpdRequest.request_no.like(f"NPD-{year}-%")
    ).count()
    return f"NPD-{year}-{count + 1:04d}"


def _get_request_or_404(db: Session, request_id: int) -> NpdRequest:
    req = db.get(NpdRequest, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="NPD request not found")
    return req


def _create_steps_for_request(db: Session, npd_req: NpdRequest) -> None:
    """Create NpdStep rows from NpdStepDefinition for this request."""
    step_defs = list(
        db.scalars(select(NpdStepDefinition).order_by(NpdStepDefinition.sort_order)).all()
    )
    for step_def in step_defs:
        applies_to = json.loads(step_def.applies_to)
        # Empty applies_to means applies to all; otherwise check request_type
        if applies_to and npd_req.request_type not in applies_to:
            status = "n_a"
        else:
            status = "not_started"
        db.add(NpdStep(
            request_id=npd_req.id,
            step_code=step_def.step_code,
            status=status,
            sort_order=step_def.sort_order,
        ))


def _recalculate_request_status(db: Session, npd_req: NpdRequest) -> None:
    """Auto-update request status based on blocking step completion."""
    step_defs = {
        sd.step_code: sd
        for sd in db.scalars(select(NpdStepDefinition)).all()
    }
    all_blocking_complete = all(
        step.status in ("completed", "n_a")
        for step in npd_req.steps
        if step_defs.get(step.step_code) is not None
        and step_defs[step.step_code].is_blocking
    )
    if all_blocking_complete and npd_req.steps:
        npd_req.status = "completed"


# ---------------------------------------------------------------------------
# List / Board
# ---------------------------------------------------------------------------


@router.get("/npd")
async def npd_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    status: Optional[str] = Query(default=None),
    request_type: Optional[str] = Query(default=None),
    division: Optional[str] = Query(default=None),
):
    q = select(NpdRequest).order_by(NpdRequest.created_at.desc())
    if status:
        q = q.where(NpdRequest.status == status)
    if request_type:
        q = q.where(NpdRequest.request_type == request_type)
    if division:
        q = q.where(NpdRequest.division_code == division)
    npd_requests = list(db.scalars(q).all())

    step_defs = list(
        db.scalars(select(NpdStepDefinition).order_by(NpdStepDefinition.sort_order)).all()
    )
    divisions = list(db.scalars(select(NpdDivision).order_by(NpdDivision.label)).all())

    return templates.TemplateResponse(
        "npd_list.html",
        {
            "request": request,
            "user": user,
            "npd_requests": npd_requests,
            "step_defs": step_defs,
            "divisions": divisions,
            "request_types": REQUEST_TYPES,
            "request_from_choices": REQUEST_FROM_CHOICES,
            "filter_status": status or "",
            "filter_type": request_type or "",
            "filter_division": division or "",
        },
    )


@router.get("/npd/board")
async def npd_board(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    npd_requests = list(db.scalars(select(NpdRequest)).all())
    step_defs = list(
        db.scalars(select(NpdStepDefinition).order_by(NpdStepDefinition.sort_order)).all()
    )
    by_status: dict[str, list[NpdRequest]] = {
        "in_progress": [],
        "on_hold": [],
        "completed": [],
        "cancelled": [],
    }
    for r in npd_requests:
        by_status.setdefault(r.status, []).append(r)

    return templates.TemplateResponse(
        "npd_board.html",
        {
            "request": request,
            "user": user,
            "by_status": by_status,
            "step_defs": step_defs,
        },
    )


@router.get("/npd/emails")
async def npd_emails(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    unmatched = list(
        db.scalars(
            select(NpdEmailEvent)
            .where(NpdEmailEvent.applied.is_(False))
            .order_by(NpdEmailEvent.received_at.desc())
        ).all()
    )
    return templates.TemplateResponse(
        "npd_emails.html",
        {
            "request": request,
            "user": user,
            "email_events": unmatched,
        },
    )


# ---------------------------------------------------------------------------
# Create request
# ---------------------------------------------------------------------------


@router.post("/npd")
async def npd_create(
    request_type: str = Form(...),
    request_from: str = Form(...),
    division_code: str = Form(...),
    bulk_sku: str = Form(""),
    fg_sku: str = Form(""),
    warehouse_plants: str = Form(""),
    target_date: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    target_dt: Optional[date] = None
    if target_date.strip():
        try:
            target_dt = date.fromisoformat(target_date.strip())
        except ValueError:
            target_dt = None

    # Parse warehouse plants as JSON list or newline/comma separated
    plants_list: List[str] = []
    if warehouse_plants.strip():
        plants_list = [p.strip() for p in warehouse_plants.replace(",", "\n").splitlines() if p.strip()]

    request_no = _generate_request_no(db)
    npd_req = NpdRequest(
        request_no=request_no,
        status="in_progress",
        request_type=request_type,
        request_from=request_from,
        division_code=division_code,
        entered_by_id=user.id,
        target_date=target_dt,
        bulk_sku=bulk_sku.strip().upper() or None,
        fg_sku=fg_sku.strip().upper() or None,
        warehouse_plants=json.dumps(plants_list),
        notes=notes.strip(),
    )
    db.add(npd_req)
    db.flush()
    _create_steps_for_request(db, npd_req)
    db.commit()
    return RedirectResponse(url=f"/npd/{npd_req.id}", status_code=303)


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------


@router.get("/npd/{request_id}")
async def npd_detail(
    request_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    msg: Optional[str] = Query(default=None),
):
    npd_req = _get_request_or_404(db, request_id)
    step_defs = {
        sd.step_code: sd
        for sd in db.scalars(select(NpdStepDefinition)).all()
    }
    email_events = list(
        db.scalars(
            select(NpdEmailEvent)
            .where(NpdEmailEvent.request_id == request_id)
            .order_by(NpdEmailEvent.received_at.desc())
        ).all()
    )
    divisions = list(db.scalars(select(NpdDivision).order_by(NpdDivision.label)).all())

    return templates.TemplateResponse(
        "npd_detail.html",
        {
            "request": request,
            "user": user,
            "npd_req": npd_req,
            "step_defs": step_defs,
            "email_events": email_events,
            "divisions": divisions,
            "request_types": REQUEST_TYPES,
            "request_from_choices": REQUEST_FROM_CHOICES,
            "msg": msg,
        },
    )


@router.post("/npd/{request_id}/edit")
async def npd_edit(
    request_id: int,
    status: str = Form(...),
    request_type: str = Form(...),
    request_from: str = Form(...),
    division_code: str = Form(...),
    bulk_sku: str = Form(""),
    fg_sku: str = Form(""),
    warehouse_plants: str = Form(""),
    target_date: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    npd_req = _get_request_or_404(db, request_id)
    target_dt: Optional[date] = None
    if target_date.strip():
        try:
            target_dt = date.fromisoformat(target_date.strip())
        except ValueError:
            target_dt = None

    plants_list: List[str] = []
    if warehouse_plants.strip():
        plants_list = [p.strip() for p in warehouse_plants.replace(",", "\n").splitlines() if p.strip()]

    npd_req.status = status
    npd_req.request_type = request_type
    npd_req.request_from = request_from
    npd_req.division_code = division_code
    npd_req.bulk_sku = bulk_sku.strip().upper() or None
    npd_req.fg_sku = fg_sku.strip().upper() or None
    npd_req.warehouse_plants = json.dumps(plants_list)
    npd_req.target_date = target_dt
    npd_req.notes = notes.strip()
    db.commit()
    return RedirectResponse(url=f"/npd/{request_id}", status_code=303)


# ---------------------------------------------------------------------------
# Step update
# ---------------------------------------------------------------------------


@router.post("/npd/{request_id}/step/{code}")
async def npd_step_update(
    request_id: int,
    code: str,
    status: str = Form(...),
    notes: str = Form(""),
    batch_number: str = Form(""),
    scheduled_date: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    npd_req = _get_request_or_404(db, request_id)

    step = (
        db.query(NpdStep)
        .filter(NpdStep.request_id == request_id, NpdStep.step_code == code)
        .first()
    )
    if step is None:
        raise HTTPException(status_code=404, detail="Step not found")

    # Blocking check: all previous blocking steps must be completed
    if status not in ("n_a", "not_started"):
        step_defs = {
            sd.step_code: sd
            for sd in db.scalars(select(NpdStepDefinition)).all()
        }
        predecessor_steps = [
            s for s in npd_req.steps
            if s.sort_order < step.sort_order and s.status != "n_a"
            and step_defs.get(s.step_code) is not None
            and step_defs[s.step_code].is_blocking
        ]
        incomplete_blockers = [s for s in predecessor_steps if s.status != "completed"]
        if incomplete_blockers:
            blocker_labels = [
                step_defs.get(s.step_code).label if step_defs.get(s.step_code) else s.step_code
                for s in incomplete_blockers
            ]
            msg = f"Cannot advance: blocking step(s) not complete: {', '.join(blocker_labels)}"
            return RedirectResponse(url=f"/npd/{request_id}?msg={msg}", status_code=303)

    step.status = status
    step.notes = notes.strip()
    if batch_number.strip():
        step.batch_number = batch_number.strip()
    if scheduled_date.strip():
        step.scheduled_date = scheduled_date.strip()
    if status == "completed":
        step.completed_at = datetime.utcnow()
        step.completed_by_id = user.id
    else:
        step.completed_at = None
        step.completed_by_id = None

    # Recalculate request status
    _recalculate_request_status(db, npd_req)
    db.commit()
    return RedirectResponse(url=f"/npd/{request_id}", status_code=303)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


@router.post("/npd/{request_id}/comment")
async def npd_add_comment(
    request_id: int,
    body: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    npd_req = _get_request_or_404(db, request_id)
    if body.strip():
        db.add(NpdComment(
            request_id=npd_req.id,
            user_id=user.id,
            body=body.strip(),
        ))
        db.commit()
    return RedirectResponse(url=f"/npd/{request_id}", status_code=303)


# ---------------------------------------------------------------------------
# Email paste
# ---------------------------------------------------------------------------


@router.post("/npd/{request_id}/paste-email")
async def npd_paste_email(
    request_id: int,
    email_text: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    _get_request_or_404(db, request_id)
    result = parse_email(subject="", body=email_text, db=db)
    now = datetime.utcnow()
    if result.confidence > 0.5:
        apply_email_event(
            db=db,
            result=result,
            source="manual_paste",
            sender="",
            subject="",
            body=email_text,
            received_at=now,
        )
        db.commit()
        msg = f"Email applied: step '{result.step_code}' → {result.new_status}"
    else:
        # Still save the event as unapplied
        result.request_id = request_id
        apply_email_event(
            db=db,
            result=result,
            source="manual_paste",
            sender="",
            subject="",
            body=email_text,
            received_at=now,
        )
        db.commit()
        msg = "Email saved but could not be automatically matched (low confidence)"

    return RedirectResponse(url=f"/npd/{request_id}?msg={msg}", status_code=303)


# ---------------------------------------------------------------------------
# Apply email event manually
# ---------------------------------------------------------------------------


@router.post("/npd/emails/{event_id}/apply")
async def npd_email_apply(
    event_id: int,
    request_id: int = Form(...),
    step_code: str = Form(...),
    new_status: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    event = db.get(NpdEmailEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Email event not found")

    step = (
        db.query(NpdStep)
        .filter(NpdStep.request_id == request_id, NpdStep.step_code == step_code)
        .first()
    )
    if step and step.status not in ("completed", "n_a"):
        step.status = new_status
        if new_status == "completed":
            step.completed_at = datetime.utcnow()
            step.completed_by_id = user.id
        event.applied = True
        event.request_id = request_id
        event.matched_step_code = step_code
        event.matched_status = new_status

        npd_req = db.get(NpdRequest, request_id)
        if npd_req:
            _recalculate_request_status(db, npd_req)

    db.commit()
    return RedirectResponse(url="/npd/emails", status_code=303)
