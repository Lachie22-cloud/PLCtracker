"""Authentication: password hashing, session cookies, current-user dependency."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_serializer = URLSafeTimedSerializer(settings.secret_key, salt="plct-session")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def issue_session_token(user_id: int) -> str:
    return _serializer.dumps({"uid": user_id})


def read_session_token(token: str) -> Optional[int]:
    try:
        data = _serializer.loads(token, max_age=settings.session_max_age_s)
    except BadSignature:
        return None
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    uid = data.get("uid")
    return int(uid) if uid is not None else None


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> Optional[User]:
    token = request.cookies.get(settings.session_cookie)
    if not token:
        return None
    uid = read_session_token(token)
    if uid is None:
        return None
    user = db.query(User).filter(User.id == uid, User.is_active.is_(True)).first()
    return user


def require_user(
    request: Request, user: Optional[User] = Depends(get_current_user)
) -> User:
    if user is None:
        # Redirect for HTML requests, else 401
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            raise HTTPException(
                status_code=status.HTTP_303_SEE_OTHER,
                headers={"Location": f"/login?next={request.url.path}"},
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


def redirect_to_login(next_path: str = "/") -> RedirectResponse:
    return RedirectResponse(url=f"/login?next={next_path}", status_code=303)
