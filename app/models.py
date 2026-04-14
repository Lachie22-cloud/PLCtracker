"""SQLAlchemy ORM models for PLCtracker."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------


class LifecycleStage(Base):
    __tablename__ = "lifecycle_stage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    family: Mapped[str] = mapped_column(String(32), nullable=False, default="Other")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    color: Mapped[str] = mapped_column(String(16), nullable=False, default="#888888")
    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Plant(Base):
    __tablename__ = "plant"

    plant_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    plant_type: Mapped[str] = mapped_column(String(16), nullable=False, default="warehouse")
    description: Mapped[str] = mapped_column(String(128), nullable=False, default="")


class MrpRule(Base):
    """Expected MRP profile per (plant, stage). plant NULL = applies to all plants."""

    __tablename__ = "mrp_rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plant_code: Mapped[Optional[str]] = mapped_column(
        String(16), ForeignKey("plant.plant_code"), nullable=True
    )
    stage_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("lifecycle_stage.code"), nullable=False
    )
    expected_mrp_profile: Mapped[str] = mapped_column(String(16), nullable=False)

    __table_args__ = (
        Index("ix_mrp_rule_lookup", "stage_code", "plant_code"),
        UniqueConstraint("plant_code", "stage_code", name="uq_mrp_rule_plant_stage"),
    )


# ---------------------------------------------------------------------------
# Users / auth
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="editor")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


# ---------------------------------------------------------------------------
# Core product state
# ---------------------------------------------------------------------------


class Product(Base):
    """Current state per (material_no, plant). Upserted on every snapshot."""

    __tablename__ = "product"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    material_no: Mapped[str] = mapped_column(String(64), nullable=False)
    plant_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("plant.plant_code"), nullable=False
    )
    stage_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("lifecycle_stage.code"), nullable=False
    )
    mrp_profile: Mapped[str] = mapped_column(String(16), nullable=False, default="")

    owner_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=True
    )

    mrp_mismatch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mrp_mismatch_note: Mapped[str] = mapped_column(Text, nullable=False, default="")

    family_mismatch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    family_mismatch_note: Mapped[str] = mapped_column(Text, nullable=False, default="")

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    stage_since: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    owner: Mapped[Optional[User]] = relationship("User")

    __table_args__ = (
        UniqueConstraint("material_no", "plant_code", name="uq_product_matnr_plant"),
        Index("ix_product_material", "material_no"),
        Index("ix_product_stage", "stage_code"),
        Index("ix_product_plant", "plant_code"),
    )


class Comment(Base):
    __tablename__ = "comment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("product.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship("User")


class Action(Base):
    __tablename__ = "action"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("product.id"), nullable=False
    )
    created_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=False
    )
    assignee_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_by: Mapped[User] = relationship("User", foreign_keys=[created_by_id])
    assignee: Mapped[Optional[User]] = relationship("User", foreign_keys=[assignee_id])


# ---------------------------------------------------------------------------
# History: snapshots, rows, transitions
# ---------------------------------------------------------------------------


class Snapshot(Base):
    __tablename__ = "snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    uploaded_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    uploader: Mapped[User] = relationship("User")


class SnapshotRow(Base):
    __tablename__ = "snapshot_row"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("snapshot.id"), nullable=False, index=True
    )
    material_no: Mapped[str] = mapped_column(String(64), nullable=False)
    plant_code: Mapped[str] = mapped_column(String(16), nullable=False)
    stage_code: Mapped[str] = mapped_column(String(16), nullable=False)
    mrp_profile: Mapped[str] = mapped_column(String(16), nullable=False, default="")

    __table_args__ = (
        Index("ix_snapshot_row_lookup", "snapshot_id", "material_no", "plant_code"),
    )


class StageTransition(Base):
    __tablename__ = "stage_transition"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("product.id"), nullable=False, index=True
    )
    from_stage_code: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    to_stage_code: Mapped[str] = mapped_column(String(16), nullable=False)
    from_snapshot_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("snapshot.id"), nullable=True
    )
    to_snapshot_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("snapshot.id"), nullable=False
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
