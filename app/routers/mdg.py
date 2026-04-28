"""Serve the MDG React frontend SPA as the main UI."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse
from starlette.responses import Response

DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
INDEX = DIST / "index.html"

router = APIRouter()


@router.get("/", response_model=None, include_in_schema=False)
@router.get("/{path:path}", response_model=None, include_in_schema=False)
async def spa_fallback(path: str = "") -> Response:
    if not INDEX.exists():
        return JSONResponse({"detail": "frontend not built"}, status_code=404)
    return FileResponse(INDEX)
