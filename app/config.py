"""Runtime configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(name: str, default: str = "") -> str:
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
    # SAP OData
    sap_odata_base_url: str = ""
    sap_odata_user: str = ""
    sap_odata_password: str = ""
    sap_odata_mara_entity: str = "A_Product"
    sap_odata_marc_entity: str = "A_ProductPlant"
    # Scheduler
    scheduler_enabled: bool = True
    extraction_cron: str = "0 2 * * *"
    extraction_delta: bool = True


def load_settings() -> Settings:
    db_path = Path(_env("PLCT_DB_PATH", str(Path.cwd() / "data" / "app.db")))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    secret_key = _env("PLCT_SECRET_KEY", "dev-insecure-change-me")
    admin_email = _env("PLCT_ADMIN_EMAIL", "admin@example.com")
    admin_password = _env("PLCT_ADMIN_PASSWORD", "changeme")
    admin_name = _env("PLCT_ADMIN_NAME", "Admin")
    sap_odata_base_url = _env("PLCT_SAP_ODATA_BASE_URL", "") or ""
    sap_odata_user = _env("PLCT_SAP_ODATA_USER", "") or ""
    sap_odata_password = _env("PLCT_SAP_ODATA_PASSWORD", "") or ""
    sap_odata_mara_entity = _env("PLCT_SAP_ODATA_MARA_ENTITY", "A_Product") or "A_Product"
    sap_odata_marc_entity = _env("PLCT_SAP_ODATA_MARC_ENTITY", "A_ProductPlant") or "A_ProductPlant"
    scheduler_enabled = (_env("PLCT_SCHEDULER_ENABLED", "false") or "false").lower() not in ("false", "0", "no")
    extraction_cron = _env("PLCT_EXTRACTION_CRON", "0 2 * * *") or "0 2 * * *"
    extraction_delta = (_env("PLCT_EXTRACTION_DELTA", "true") or "true").lower() not in ("false", "0", "no")
    return Settings(
        db_path=db_path,
        secret_key=secret_key,
        admin_email=admin_email,
        admin_password=admin_password,
        admin_name=admin_name,
        sap_odata_base_url=sap_odata_base_url,
        sap_odata_user=sap_odata_user,
        sap_odata_password=sap_odata_password,
        sap_odata_mara_entity=sap_odata_mara_entity,
        sap_odata_marc_entity=sap_odata_marc_entity,
        scheduler_enabled=scheduler_enabled,
        extraction_cron=extraction_cron,
        extraction_delta=extraction_delta,
    )


settings = load_settings()
