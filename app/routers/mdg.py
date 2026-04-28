"""Serve the MDG React frontend SPA at /mdg/*."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
INDEX = DIST / "index.html"

router = APIRouter()

# Mounted separately in main.py: StaticFiles at /mdg/assets
# This router catches all other /mdg paths and returns index.html for SPA routing.


@router.get("/mdg", include_in_schema=False)
@router.get("/mdg/{path:path}", include_in_schema=False)
async def mdg_spa(path: str = "") -> FileResponse:
    return FileResponse(INDEX)
