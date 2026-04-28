"""Shared pytest fixtures: isolated in-memory DB for each test."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    """Point PLCT_DB_PATH at a temp file and reload the app to pick it up."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("PLCT_DB_PATH", str(db_path))
    monkeypatch.setenv("PLCT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("PLCT_ADMIN_EMAIL", "admin@test.local")
    monkeypatch.setenv("PLCT_ADMIN_PASSWORD", "admin-pw")

    # Reload config + db + bootstrap to pick up the env vars
    import importlib
    from app import config, db, bootstrap  # noqa

    importlib.reload(config)
    importlib.reload(db)
    # models & services import db.Base; they must be reloaded after db
    from app import models

    importlib.reload(models)
    from app.services import snapshot as snapshot_mod

    importlib.reload(snapshot_mod)
    importlib.reload(bootstrap)

    bootstrap.bootstrap()

    yield

    # cleanup handled by tmp_path
