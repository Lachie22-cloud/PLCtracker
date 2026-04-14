"""Login / logout routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..auth import (
    get_current_user,
    issue_session_token,
    verify_password,
)
from ..config import settings
from ..db import get_db
from ..models import User
from ..templating import templates


router = APIRouter()


@router.get("/login")
async def login_form(request: Request, next: str = "/", error: str | None = None):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "next": next, "error": error, "user": None},
    )


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "next": next,
                "error": "Invalid email or password.",
                "user": None,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    token = issue_session_token(user.id)
    # Ensure next is a local path
    if not next.startswith("/"):
        next = "/"
    resp = RedirectResponse(url=next, status_code=303)
    resp.set_cookie(
        settings.session_cookie,
        token,
        max_age=settings.session_max_age_s,
        httponly=True,
        samesite="lax",
        secure=False,  # flip to True behind HTTPS in production
    )
    return resp


@router.post("/logout")
async def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie(settings.session_cookie)
    return resp


@router.get("/")
async def root(
    request: Request, user: User | None = Depends(get_current_user)
):
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    return RedirectResponse(url="/board", status_code=303)
