"""FastAPI entrypoint for PLCtracker."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .bootstrap import bootstrap
from .routers import admin, auth, dashboard, export, governance, mdg, npd, presets, products, review, upload


app = FastAPI(title="PLCtracker", version="0.1.0")

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

MDG_ASSETS = Path(__file__).resolve().parents[1] / "frontend" / "dist" / "assets"
if MDG_ASSETS.is_dir():
    app.mount("/assets", StaticFiles(directory=str(MDG_ASSETS)), name="mdg-assets")


@app.on_event("startup")
async def _startup() -> None:
    bootstrap()


# /healthz must be registered before the SPA catch-all router
@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}


app.include_router(auth.router)
app.include_router(products.router)
app.include_router(dashboard.router)
app.include_router(review.router)
app.include_router(upload.router)
app.include_router(export.router)
app.include_router(admin.router)
app.include_router(governance.router)
app.include_router(presets.router)
app.include_router(npd.router)
# SPA catch-all must be last so all API routes take priority
app.include_router(mdg.router)
