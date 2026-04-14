"""Idempotent bootstrap: create tables + seed reference data + admin user."""
from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy.orm import Session

from .auth import hash_password
from .config import settings
from .db import Base, engine, db_session
from .models import LifecycleStage, MrpRule, Plant, User


SEED_DIR = Path(__file__).resolve().parent.parent / "seed"


def _seed_stages(db: Session) -> None:
    if db.query(LifecycleStage).count() > 0:
        return
    path = SEED_DIR / "stages.csv"
    with path.open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            db.add(
                LifecycleStage(
                    code=row["code"].strip(),
                    label=row["label"].strip(),
                    family=row["family"].strip(),
                    display_order=int(row["display_order"]),
                    color=row["color"].strip(),
                    is_terminal=row["is_terminal"].strip().lower() in ("1", "true", "yes"),
                )
            )


def _seed_plants(db: Session) -> None:
    if db.query(Plant).count() > 0:
        return
    path = SEED_DIR / "plants.csv"
    with path.open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            db.add(
                Plant(
                    plant_code=row["plant_code"].strip(),
                    plant_type=row["plant_type"].strip(),
                    description=row["description"].strip(),
                )
            )


def _seed_mrp_rules(db: Session) -> None:
    if db.query(MrpRule).count() > 0:
        return
    path = SEED_DIR / "mrp_rules.csv"
    with path.open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            plant = row["plant_code"].strip() or None
            db.add(
                MrpRule(
                    plant_code=plant,
                    stage_code=row["stage_code"].strip(),
                    expected_mrp_profile=row["expected_mrp_profile"].strip(),
                )
            )


def _ensure_admin(db: Session) -> None:
    existing = db.query(User).filter(User.email == settings.admin_email).first()
    if existing:
        return
    db.add(
        User(
            email=settings.admin_email,
            name=settings.admin_name,
            password_hash=hash_password(settings.admin_password),
            role="admin",
            is_active=True,
        )
    )


def bootstrap() -> None:
    """Create tables and seed data. Safe to call on every startup."""
    Base.metadata.create_all(bind=engine)
    with db_session() as db:
        _seed_stages(db)
        db.flush()
        _seed_plants(db)
        db.flush()
        _seed_mrp_rules(db)
        _ensure_admin(db)
