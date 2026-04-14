"""Runtime configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


@dataclass(frozen=True)
class Settings:
    db_path: Path
    secret_key: str
    admin_email: str
    admin_password: str
    admin_name: str
    session_cookie: str = "plct_session"
    session_max_age_s: int = 60 * 60 * 8  # 8 hours
    max_upload_mb: int = 25


def load_settings() -> Settings:
    db_path = Path(_env("PLCT_DB_PATH", str(Path.cwd() / "data" / "app.db")))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    secret_key = _env("PLCT_SECRET_KEY", "dev-insecure-change-me")
    admin_email = _env("PLCT_ADMIN_EMAIL", "admin@example.com")
    admin_password = _env("PLCT_ADMIN_PASSWORD", "changeme")
    admin_name = _env("PLCT_ADMIN_NAME", "Admin")
    return Settings(
        db_path=db_path,
        secret_key=secret_key,
        admin_email=admin_email,
        admin_password=admin_password,
        admin_name=admin_name,
    )


settings = load_settings()
