"""Upload SAP extract; parse, snapshot, upsert, validate."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..auth import require_user
from ..db import get_db
from ..models import User
from ..services.snapshot import UploadParseError, process_upload
from ..templating import templates

router = APIRouter()


@router.get("/upload")
async def upload_form(
    request: Request,
    user: User = Depends(require_user),
    error: str | None = None,
):
    return templates.TemplateResponse(
        "upload.html",
        {"request": request, "user": user, "error": error, "summary": None},
    )


@router.post("/upload")
async def upload_submit(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    content = await file.read()
    try:
        summary = process_upload(
            db,
            content=content,
            filename=file.filename or "upload.csv",
            uploaded_by_id=user.id,
        )
    except UploadParseError as exc:
        return templates.TemplateResponse(
            "upload.html",
            {"request": request, "user": user, "error": str(exc), "summary": None},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    db.commit()
    return templates.TemplateResponse(
        "upload.html",
        {"request": request, "user": user, "error": None, "summary": summary},
    )
