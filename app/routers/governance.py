"""Governance: violations list, material change history, manual extraction trigger."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..db import get_db
from ..models import (
    ExtractionRun,
    GovernanceRule,
    GovernanceViolation,
    Marc,
    MarcChange,
    Material,
)
from ..services.extract import run_extraction
from ..templating import templates

router = APIRouter()


@router.get("/governance/violations")
async def violations_list(
    request: Request,
    field_name: Optional[str] = None,
    werks: Optional[str] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    q = (
        select(GovernanceViolation)
        .where(GovernanceViolation.resolved_at.is_(None))
        .order_by(GovernanceViolation.detected_at.desc())
    )
    if field_name:
        q = q.where(GovernanceViolation.field_name == field_name.upper())
    if werks:
        q = q.where(GovernanceViolation.werks == werks.upper())
    violations = list(db.scalars(q).all())

    # Filter by severity (requires joining rule)
    if severity:
        violations = [v for v in violations if v.rule and v.rule.severity == severity]

    # Summary counts by field
    field_counts: dict[str, int] = {}
    for v in violations:
        field_counts[v.field_name] = field_counts.get(v.field_name, 0) + 1

    return templates.TemplateResponse(
        "governance_violations.html",
        {
            "request": request,
            "user": user,
            "violations": violations,
            "field_counts": field_counts,
            "filter_field": field_name or "",
            "filter_werks": werks or "",
            "filter_severity": severity or "",
        },
    )


@router.get("/governance/material/{matnr}/changes")
async def material_changes(
    matnr: str,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    changes = list(
        db.scalars(
            select(MarcChange)
            .where(MarcChange.matnr == matnr)
            .order_by(MarcChange.detected_at.desc())
            .limit(200)
        ).all()
    )
    material = db.get(Material, matnr)
    marc_rows = list(
        db.scalars(select(Marc).where(Marc.matnr == matnr)).all()
    )
    return templates.TemplateResponse(
        "governance_changes.html",
        {
            "request": request,
            "user": user,
            "matnr": matnr,
            "material": material,
            "changes": changes,
            "marc_rows": marc_rows,
        },
    )


@router.get("/governance/runs")
async def extraction_runs(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    runs = list(
        db.scalars(
            select(ExtractionRun).order_by(ExtractionRun.started_at.desc()).limit(50)
        ).all()
    )
    return templates.TemplateResponse(
        "governance_runs.html",
        {
            "request": request,
            "user": user,
            "runs": runs,
        },
    )


@router.post("/governance/run-now")
async def run_now(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    summary = run_extraction(source="odata", trigger="manual", db=db)
    if summary.error:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {summary.error}")
    return RedirectResponse(url="/governance/runs", status_code=303)


@router.get("/governance/rules")
async def rules_list(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    rules = list(
        db.scalars(select(GovernanceRule).order_by(GovernanceRule.field_name)).all()
    )
    return templates.TemplateResponse(
        "governance_rules.html",
        {
            "request": request,
            "user": user,
            "rules": rules,
        },
    )


@router.post("/governance/rules")
async def create_rule(
    field_name: str = Form(...),
    scope_mtart: str = Form(""),
    scope_plant_code: str = Form(""),
    scope_stage_code: str = Form(""),
    expected_value: str = Form(""),
    allowed_values: str = Form(""),
    severity: str = Form("error"),
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    db.add(
        GovernanceRule(
            field_name=field_name.strip().upper(),
            scope_mtart=scope_mtart.strip() or None,
            scope_plant_code=scope_plant_code.strip().upper() or None,
            scope_stage_code=scope_stage_code.strip().upper() or None,
            expected_value=expected_value.strip() or None,
            allowed_values=allowed_values.strip() or None,
            severity=severity.strip() or "error",
        )
    )
    db.commit()
    return RedirectResponse(url="/governance/rules", status_code=303)


@router.post("/governance/rules/{rule_id}/delete")
async def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    rule = db.get(GovernanceRule, rule_id)
    if rule:
        db.delete(rule)
        db.commit()
    return RedirectResponse(url="/governance/rules", status_code=303)
