"""Tests for the v2 detail-view additions: tags, review date, manual stage
change with rationale, overrun detection."""
from __future__ import annotations

from datetime import datetime, timedelta


def _csv(rows):
    header = "Material,Plant,Plant-sp.matl status,MRP profile\n"
    body = "\n".join(",".join(r) for r in rows) + "\n"
    return (header + body).encode()


def _admin_id(db):
    from app.models import User
    return db.query(User).filter(User.role == "admin").first().id


def test_tag_library_seeded():
    from app.db import db_session
    from app.models import Tag
    with db_session() as db:
        codes = [t.code for t in db.query(Tag).all()]
        assert "slob" in codes
        assert "obs_candidate" in codes


def test_expected_days_seeded_for_n2():
    from app.db import db_session
    from app.models import LifecycleStage
    with db_session() as db:
        n2_days = db.query(LifecycleStage.expected_days).filter(LifecycleStage.code == "N2").scalar()
        a1_days = db.query(LifecycleStage.expected_days).filter(LifecycleStage.code == "A1").scalar()
    assert n2_days == 180
    assert a1_days is None  # no limit for active


def test_manual_stage_change_creates_transition_with_rationale():
    from app.db import db_session
    from app.models import Product, StageTransition
    from app.services.snapshot import process_upload

    with db_session() as db:
        uid = _admin_id(db)
        process_upload(
            db, content=_csv([("X-1", "QF00", "A1", "MTSF")]),
            filename="t.csv", uploaded_by_id=uid,
        )
        p = db.query(Product).filter(Product.material_no == "X-1").one()

        # Simulate the route logic inline
        now = datetime.utcnow()
        db.add(
            StageTransition(
                product_id=p.id,
                from_stage_code=p.stage_code,
                to_stage_code="O1",
                from_snapshot_id=None,
                to_snapshot_id=None,
                detected_at=now,
                rationale="Demand team flagged for obsoletion 12 Apr",
                changed_by_id=uid,
            )
        )
        p.stage_code = "O1"
        p.stage_since = now

    with db_session() as db:
        p = db.query(Product).filter(Product.material_no == "X-1").one()
        assert p.stage_code == "O1"
        ts = list(db.query(StageTransition).filter(StageTransition.product_id == p.id).all())
        # One upload-driven + one manual
        assert len(ts) == 2
        manual = [t for t in ts if t.rationale][0]
        assert manual.from_stage_code == "A1"
        assert manual.to_stage_code == "O1"
        assert "Demand team" in manual.rationale
        assert manual.changed_by_id == uid
        assert manual.to_snapshot_id is None  # manual change, no snapshot


def test_tag_attach_and_detach():
    from app.db import db_session
    from app.models import Product, ProductTag, Tag
    from app.services.snapshot import process_upload

    with db_session() as db:
        uid = _admin_id(db)
        process_upload(
            db, content=_csv([("Y-1", "NW00", "A1", "MTSW")]),
            filename="t.csv", uploaded_by_id=uid,
        )
        p = db.query(Product).filter(Product.material_no == "Y-1").one()
        slob = db.query(Tag).filter(Tag.code == "slob").one()
        db.add(ProductTag(product_id=p.id, tag_id=slob.id, created_by_id=uid))

    with db_session() as db:
        p = db.query(Product).filter(Product.material_no == "Y-1").one()
        slob_id = db.query(Tag.id).filter(Tag.code == "slob").scalar()
        assert [t.code for t in p.tags] == ["slob"]

        db.query(ProductTag).filter(
            ProductTag.product_id == p.id,
            ProductTag.tag_id == slob_id,
        ).delete()

    with db_session() as db:
        p = db.query(Product).filter(Product.material_no == "Y-1").one()
        assert [t.code for t in p.tags] == []


def test_review_date_and_note_roundtrip():
    from app.db import db_session
    from app.models import Product
    from app.services.snapshot import process_upload

    with db_session() as db:
        uid = _admin_id(db)
        process_upload(
            db, content=_csv([("Z-1", "QF00", "O1", "NOPL")]),
            filename="t.csv", uploaded_by_id=uid,
        )
        p = db.query(Product).filter(Product.material_no == "Z-1").one()
        p.next_review_date = datetime.utcnow() + timedelta(days=14)
        p.review_note = "Discuss at May obs meeting"

    with db_session() as db:
        p = db.query(Product).filter(Product.material_no == "Z-1").one()
        assert p.next_review_date is not None
        assert p.review_note == "Discuss at May obs meeting"


def test_overrun_detection_based_on_expected_days():
    from app.db import db_session
    from app.models import LifecycleStage, Product
    from app.services.snapshot import process_upload

    # N2 has expected_days=180 per seed; make the product's stage_since 200d ago
    with db_session() as db:
        uid = _admin_id(db)
        process_upload(
            db, content=_csv([("OVER-1", "QF00", "N2", "MTSF")]),
            filename="t.csv", uploaded_by_id=uid,
        )
        p = db.query(Product).filter(Product.material_no == "OVER-1").one()
        p.stage_since = datetime.utcnow() - timedelta(days=200)

    with db_session() as db:
        p = db.query(Product).filter(Product.material_no == "OVER-1").one()
        n2 = db.query(LifecycleStage).filter(LifecycleStage.code == "N2").one()
        days = (datetime.utcnow() - p.stage_since).days
        assert days > n2.expected_days  # overrun condition used by the template
