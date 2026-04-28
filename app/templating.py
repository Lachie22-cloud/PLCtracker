"""Shared Jinja2 Templates object so all routers use the same env/filters."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _days_since(dt: datetime | None) -> int:
    if dt is None:
        return 0
    return max(0, (datetime.utcnow() - dt).days)


def _fmt_date(dt: datetime | None) -> str:
    if dt is None:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M")


def _from_json(value: Any) -> Any:
    """Parse a JSON string, returning the Python object (list, dict, etc.)."""
    if value is None:
        return []
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return []


templates.env.filters["days_since"] = _days_since
templates.env.filters["fmt_date"] = _fmt_date
templates.env.filters["from_json"] = _from_json
