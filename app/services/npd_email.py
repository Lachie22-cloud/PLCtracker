"""NPD email parsing service."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from ..models import NpdEmailEvent, NpdRequest, NpdStep

# Default keyword → (step_code, status) map
KEYWORD_MAP: List[Tuple[str, str, str]] = [
    ("warehouse extension complete", "warehouse_ext", "completed"),
    ("warehouse ext complete", "warehouse_ext", "completed"),
    ("bulk master data complete", "bulk_master_data", "completed"),
    ("fg master data complete", "fg_master_data", "completed"),
    ("routings setup complete", "fg_routings", "completed"),
    ("fg routings complete", "fg_routings", "completed"),
    ("fg warehouse extension complete", "fg_warehouse_ext", "completed"),
    ("costings complete", "costings", "completed"),
    ("costing complete", "costings", "completed"),
    ("ebr ready", "ebr_ready", "completed"),
    ("ebr approved", "ebr_ready", "completed"),
    ("experimental batch ready", "ebr_ready", "completed"),
    ("master data check ready", "master_data_check", "completed"),
    ("master data ready", "master_data_check", "completed"),
    ("batch raised", "batch_raised", "completed"),
    ("batch scheduled", "batch_scheduled", "completed"),
]

# SKU pattern: alphanumeric 6-20 chars
_SKU_RE = re.compile(r'\b([A-Z0-9]{6,20}(?:-[A-Z0-9]+)?)\b')


@dataclass
class ParseResult:
    request_id: Optional[int]
    step_code: Optional[str]
    new_status: Optional[str]
    confidence: float   # 0.0 - 1.0
    matched_sku: Optional[str]


def parse_email(
    subject: str,
    body: str,
    db: Session,
) -> ParseResult:
    combined = (subject + " " + body).lower()

    # Find step match
    step_code = None
    new_status = None
    for keyword, sc, st in KEYWORD_MAP:
        if keyword in combined:
            step_code = sc
            new_status = st
            break

    # Find SKU match
    request_id = None
    matched_sku = None
    sku_candidates = _SKU_RE.findall((subject + " " + body).upper())
    for sku in sku_candidates:
        req = (
            db.query(NpdRequest)
            .filter(
                (NpdRequest.bulk_sku == sku) | (NpdRequest.fg_sku == sku)
            )
            .filter(NpdRequest.status == "in_progress")
            .first()
        )
        if req:
            request_id = req.id
            matched_sku = sku
            break

    confidence = 0.0
    if request_id:
        confidence += 0.5
    if step_code:
        confidence += 0.5

    return ParseResult(
        request_id=request_id,
        step_code=step_code,
        new_status=new_status,
        confidence=confidence,
        matched_sku=matched_sku,
    )


def apply_email_event(
    db: Session,
    result: ParseResult,
    source: str,
    sender: str,
    subject: str,
    body: str,
    received_at: datetime,
) -> NpdEmailEvent:
    applied = False
    if result.request_id and result.step_code and result.new_status:
        step = (
            db.query(NpdStep)
            .filter(
                NpdStep.request_id == result.request_id,
                NpdStep.step_code == result.step_code,
            )
            .first()
        )
        if step and step.status not in ("completed", "n_a"):
            step.status = result.new_status
            if result.new_status == "completed":
                step.completed_at = received_at
            applied = True

    event = NpdEmailEvent(
        request_id=result.request_id,
        received_at=received_at,
        sender=sender,
        subject=subject,
        body_snippet=body[:500],
        matched_step_code=result.step_code,
        matched_status=result.new_status,
        applied=applied,
        source=source,
        raw_payload=json.dumps({"subject": subject, "sender": sender}),
    )
    db.add(event)
    db.flush()
    return event
