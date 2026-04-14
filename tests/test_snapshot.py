"""Unit tests for the snapshot/upload pipeline."""
from __future__ import annotations


def _csv(rows: list[tuple[str, str, str, str]]) -> bytes:
    header = "Material,Plant,Plant-sp.matl status,MRP profile\n"
    body = "\n".join(",".join(r) for r in rows) + "\n"
    return (header + body).encode()


def _get_admin_id(db):
    from app.models import User

    return db.query(User).filter(User.role == "admin").first().id


def test_parse_aliases_and_casing():
    from app.services.snapshot import parse_upload_bytes

    content = b"MATNR,WERKS,MSTAE,MRP\nabc,qf00,a1,mtsf\n"
    df = parse_upload_bytes(content, "sap.csv")
    assert list(df.columns) == ["material_no", "plant_code", "stage_code", "mrp_profile"]
    assert df.iloc[0]["stage_code"] == "A1"
    assert df.iloc[0]["plant_code"] == "QF00"
    assert df.iloc[0]["mrp_profile"] == "MTSF"


def test_upsert_and_mrp_flags():
    from app.db import db_session
    from app.models import Product
    from app.services.snapshot import process_upload

    rows = [
        ("01989176-1L", "QF00", "A1", "MTSF"),   # ok
        ("06250759-4L", "QF00", "O1", "NOPL"),   # ok (plant-agnostic rule)
        ("07528171-15L", "QF00", "A1", "NOPL"),  # MRP mismatch (expected MTSF)
    ]
    with db_session() as db:
        uid = _get_admin_id(db)
        summary = process_upload(
            db, content=_csv(rows), filename="t.csv", uploaded_by_id=uid
        )
        assert summary.row_count == 3
        assert summary.added == 3
        assert summary.mrp_mismatches == 1

        products = {(p.material_no, p.plant_code): p for p in db.query(Product).all()}
        assert products[("01989176-1L", "QF00")].mrp_mismatch is False
        assert products[("07528171-15L", "QF00")].mrp_mismatch is True


def test_family_mismatch_detection():
    from app.db import db_session
    from app.models import Product
    from app.services.snapshot import process_upload

    # Factory (QF00) has moved to O2, warehouses still A1 -> mismatch expected
    rows = [
        ("X-1", "QF00", "O2", "NOPL"),
        ("X-1", "NW00", "A1", "MTSW"),
        ("X-1", "WW00", "A1", "MTSW"),
        # Aligned family -> no mismatch
        ("Y-1", "QF00", "A1", "MTSF"),
        ("Y-1", "NW00", "A1", "MTSW"),
    ]
    with db_session() as db:
        uid = _get_admin_id(db)
        summary = process_upload(
            db, content=_csv(rows), filename="t.csv", uploaded_by_id=uid
        )
        assert summary.family_mismatches == 2  # two warehouse rows for X-1

        products = {(p.material_no, p.plant_code): p for p in db.query(Product).all()}
        assert products[("X-1", "QF00")].family_mismatch is False
        assert products[("X-1", "NW00")].family_mismatch is True
        assert products[("X-1", "WW00")].family_mismatch is True
        assert products[("Y-1", "NW00")].family_mismatch is False


def test_second_upload_detects_stage_change():
    from app.db import db_session
    from app.models import Product, StageTransition
    from app.services.snapshot import process_upload

    first = _csv([("X-1", "QF00", "A1", "MTSF")])
    second = _csv([("X-1", "QF00", "O1", "NOPL")])
    with db_session() as db:
        uid = _get_admin_id(db)
        s1 = process_upload(db, content=first, filename="1.csv", uploaded_by_id=uid)
        assert s1.added == 1 and s1.stage_changed == 0

        s2 = process_upload(db, content=second, filename="2.csv", uploaded_by_id=uid)
        assert s2.added == 0
        assert s2.updated == 1
        assert s2.stage_changed == 1

        p = db.query(Product).filter(Product.material_no == "X-1").one()
        assert p.stage_code == "O1"

        transitions = db.query(StageTransition).filter(StageTransition.product_id == p.id).all()
        # One from None->A1 (first upload) + one A1->O1 (second)
        assert len(transitions) == 2
        stage_change = [t for t in transitions if t.from_stage_code == "A1"][0]
        assert stage_change.to_stage_code == "O1"


def test_no_false_positive_when_rule_missing():
    """N1/N2 have no MRP rule seeded — rows with those statuses should not be flagged."""
    from app.db import db_session
    from app.models import Product
    from app.services.snapshot import process_upload

    rows = [("NEW-1", "QF00", "N1", "ANYTHING"), ("NEW-2", "NW00", "N2", "WHATEVER")]
    with db_session() as db:
        uid = _get_admin_id(db)
        summary = process_upload(
            db, content=_csv(rows), filename="t.csv", uploaded_by_id=uid
        )
        assert summary.mrp_mismatches == 0
        for p in db.query(Product).all():
            assert p.mrp_mismatch is False


def test_missing_required_column_raises():
    from app.services.snapshot import UploadParseError, parse_upload_bytes

    bad = b"Material,Plant,MRP profile\n01989176-1L,QF00,MTSF\n"  # no status column
    import pytest

    with pytest.raises(UploadParseError):
        parse_upload_bytes(bad, "sap.csv")
