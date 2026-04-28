"""SQLAlchemy ORM models for PLCtracker."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
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
    # Expected days in this stage before it's considered "overrun". NULL = no limit.
    expected_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Plant(Base):
    __tablename__ = "plant"

    plant_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    plant_type: Mapped[str] = mapped_column(String(16), nullable=False, default="warehouse")
    description: Mapped[str] = mapped_column(String(128), nullable=False, default="")


class SchemaMeta(Base):
    """Key-value table used to track one-shot migrations applied to the DB."""

    __tablename__ = "schema_meta"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False, default="")


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

    next_review_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_note: Mapped[str] = mapped_column(Text, nullable=False, default="")

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
    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary="product_tag",
        order_by="Tag.display_order",
        lazy="selectin",
    )

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
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="upload")

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
    to_snapshot_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("snapshot.id"), nullable=True
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    # Optional rationale set by a planner when manually changing stage.
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Who made this change — NULL for automatic (upload-driven) transitions.
    changed_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=True
    )

    changed_by: Mapped[Optional[User]] = relationship("User")


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    color: Mapped[str] = mapped_column(String(16), nullable=False, default="#64748b")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ProductTag(Base):
    __tablename__ = "product_tag"

    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("product.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=True
    )


# ---------------------------------------------------------------------------
# SAP governance: MARA / MARC canonical state
# ---------------------------------------------------------------------------


class Material(Base):
    """MARA subset — one row per matnr."""

    __tablename__ = "material"

    matnr: Mapped[str] = mapped_column(String(64), primary_key=True)
    mtart: Mapped[str] = mapped_column(String(8), nullable=False, default="")
    mbrsh: Mapped[str] = mapped_column(String(8), nullable=False, default="")
    maktx: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    meins: Mapped[str] = mapped_column(String(8), nullable=False, default="")
    matkl: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    ersda: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    laeda: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class Marc(Base):
    """Governance row per (matnr, werks) — tracks ~20 MARC fields."""

    __tablename__ = "marc"

    matnr: Mapped[str] = mapped_column(String(64), ForeignKey("material.matnr"), primary_key=True)
    werks: Mapped[str] = mapped_column(String(16), ForeignKey("plant.plant_code"), primary_key=True)

    # The tracked governance fields (all nullable — SAP may not populate every field)
    mmsta: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)   # plant-specific material status
    dispr: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)   # MRP profile
    dismm: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)    # MRP type
    dispo: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)    # MRP controller
    beskz: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)    # Procurement type
    sobsl: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)    # Special procurement
    ekgrp: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)    # Purchasing group
    disgr: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)    # MRP group
    eisbe: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)   # Safety stock
    minbe: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)   # Reorder point
    losfx: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)   # Fixed lot size
    plifz: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)    # Planned delivery time
    webaz: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)    # GR processing time
    lgpro: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)   # Issue storage location
    lgfsb: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)   # External procurement SL
    fhori: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)    # Scheduling margin key
    schgt: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)    # Bulk material flag
    perkz: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)    # Period indicator
    mtvfp: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)    # Availability check
    strgr: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)    # Strategy group

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    material: Mapped["Material"] = relationship("Material")


class MarcChange(Base):
    """Field-level audit log — one row per changed field per extraction run."""

    __tablename__ = "marc_change"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    matnr: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    werks: Mapped[str] = mapped_column(String(16), nullable=False)
    field_name: Mapped[str] = mapped_column(String(32), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    extraction_run_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("extraction_run.id"), nullable=True, index=True
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_marc_change_matnr_werks", "matnr", "werks"),
    )


class ExtractionRun(Base):
    """Record of one SAP OData extraction (or upload-triggered run)."""

    __tablename__ = "extraction_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="odata")
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    mara_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    marc_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    change_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class GovernanceRule(Base):
    """Configurable validation rule for a single MARC field.

    Specificity: scope_mtart + scope_plant_code + scope_stage_code is most specific;
    global (all NULL) is least specific. Most-specific matching rule wins.
    """

    __tablename__ = "governance_rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    field_name: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_mtart: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    scope_plant_code: Mapped[Optional[str]] = mapped_column(
        String(16), ForeignKey("plant.plant_code"), nullable=True
    )
    scope_stage_code: Mapped[Optional[str]] = mapped_column(
        String(16), ForeignKey("lifecycle_stage.code"), nullable=True
    )
    expected_value: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    allowed_values: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # CSV
    severity: Mapped[str] = mapped_column(String(8), nullable=False, default="error")

    __table_args__ = (
        Index("ix_governance_rule_field", "field_name"),
    )


class GovernanceViolation(Base):
    """One row per currently-violating (matnr, werks, field_name) tuple."""

    __tablename__ = "governance_violation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    matnr: Mapped[str] = mapped_column(String(64), nullable=False)
    werks: Mapped[str] = mapped_column(String(16), nullable=False)
    field_name: Mapped[str] = mapped_column(String(32), nullable=False)
    rule_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("governance_rule.id"), nullable=False
    )
    actual_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expected_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    rule: Mapped["GovernanceRule"] = relationship("GovernanceRule")

    __table_args__ = (
        UniqueConstraint("matnr", "werks", "field_name", name="uq_gov_violation_key"),
        Index("ix_gov_violation_matnr", "matnr"),
    )


# ---------------------------------------------------------------------------
# MARC field stats (for preset autocomplete)
# ---------------------------------------------------------------------------


class MarcFieldStats(Base):
    """Counts of observed values per MARC field — powers preset autocomplete."""

    __tablename__ = "marc_field_stats"

    field_name: Mapped[str] = mapped_column(String(32), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), primary_key=True)
    seen_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


# ---------------------------------------------------------------------------
# Material presets
# ---------------------------------------------------------------------------


class PresetPlant(Base):
    """Association: which plants use a given preset."""

    __tablename__ = "preset_plant"

    preset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("material_preset.id"), primary_key=True
    )
    plant_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("plant.plant_code"), primary_key=True
    )


class MaterialPreset(Base):
    """Named set of MARC field expectations (e.g. 'bulk', 'fg_factory')."""

    __tablename__ = "material_preset"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    preset_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    plants: Mapped[List["Plant"]] = relationship(
        "Plant",
        secondary="preset_plant",
        lazy="selectin",
    )
    fields: Mapped[List["PresetField"]] = relationship(
        "PresetField",
        order_by="PresetField.sort_order",
        lazy="selectin",
    )


class PresetField(Base):
    """One MARC field rule within a MaterialPreset."""

    __tablename__ = "preset_field"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    preset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("material_preset.id"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    is_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allowed_values: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    severity: Mapped[str] = mapped_column(String(8), nullable=False, default="error")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sap_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sap_impact: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sap_example: Mapped[str] = mapped_column(Text, nullable=False, default="")


# ---------------------------------------------------------------------------
# NPD pipeline
# ---------------------------------------------------------------------------


class NpdDivision(Base):
    """Business division — used to categorise NPD requests."""

    __tablename__ = "npd_division"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    label: Mapped[str] = mapped_column(String(128), nullable=False)


class NpdStepDefinition(Base):
    """Template definition for each step in the NPD workflow."""

    __tablename__ = "npd_step_definition"

    step_code: Mapped[str] = mapped_column(String(32), primary_key=True)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    applies_to: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class NpdRequest(Base):
    """One new-product-development request tracking a SKU through its gates."""

    __tablename__ = "npd_request"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="in_progress")
    request_type: Mapped[str] = mapped_column(String(32), nullable=False)
    request_from: Mapped[str] = mapped_column(String(32), nullable=False)
    division_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("npd_division.code"), nullable=False
    )
    entered_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    target_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    bulk_sku: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    fg_sku: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    warehouse_plants: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    entered_by: Mapped[User] = relationship("User", foreign_keys=[entered_by_id])
    steps: Mapped[List["NpdStep"]] = relationship(
        "NpdStep",
        order_by="NpdStep.sort_order",
        lazy="selectin",
    )
    comments: Mapped[List["NpdComment"]] = relationship(
        "NpdComment",
        order_by="NpdComment.created_at",
        lazy="selectin",
    )


class NpdStep(Base):
    """One step within an NpdRequest."""

    __tablename__ = "npd_step"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("npd_request.id"), nullable=False, index=True
    )
    step_code: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="not_started")
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=True
    )
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    batch_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    scheduled_date: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    completed_by: Mapped[Optional[User]] = relationship(
        "User", foreign_keys=[completed_by_id]
    )

    __table_args__ = (
        UniqueConstraint("request_id", "step_code", name="uq_npd_step_req_code"),
    )


class NpdComment(Base):
    """Comment on an NPD request."""

    __tablename__ = "npd_comment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("npd_request.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship("User")


class NpdEmailEvent(Base):
    """Record of an email (manual paste or Graph API) parsed for NPD step updates."""

    __tablename__ = "npd_email_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("npd_request.id"), nullable=True, index=True
    )
    received_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sender: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    subject: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body_snippet: Mapped[str] = mapped_column(Text, nullable=False, default="")
    matched_step_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    matched_status: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual_paste")
    raw_payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
