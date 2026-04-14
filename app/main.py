"""FastAPI entrypoint for PLCtracker."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .bootstrap import bootstrap
from .routers import admin, auth, dashboard, export, products, upload


app = FastAPI(title="PLCtracker", version="0.1.0")

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(dashboard.router)
app.include_router(upload.router)
app.include_router(export.router)
app.include_router(admin.router)


@app.on_event("startup")
async def _startup() -> None:
    bootstrap()


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}
