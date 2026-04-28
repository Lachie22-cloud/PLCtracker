"""Governance rules engine: load rules, evaluate MARC rows, rebuild violations."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import GovernanceRule, GovernanceViolation, Marc, Material, MaterialPreset


# ---------------------------------------------------------------------------
# Rule index
# ---------------------------------------------------------------------------

# Scope key: (field_name, mtart_or_None, plant_or_None, stage_or_None)
# Specificity score: count of non-None scope dimensions (0-3)
_ScopeKey = Tuple[str, Optional[str], Optional[str], Optional[str]]


@dataclass
class RuleIndex:
    _rules: List[GovernanceRule] = field(default_factory=list)

    def match(
        self,
        field_name: str,
        mtart: str,
        plant: str,
        stage: str,
    ) -> Optional[GovernanceRule]:
        """Return the most-specific rule matching this (field, mtart, plant, stage), or None."""
        candidates = [
            r for r in self._rules
            if r.field_name == field_name
            and (r.scope_mtart is None or r.scope_mtart == mtart)
            and (r.scope_plant_code is None or r.scope_plant_code == plant)
            and (r.scope_stage_code is None or r.scope_stage_code == stage)
        ]
        if not candidates:
            return None
        # Higher specificity = more non-None scope fields
        def _score(r: GovernanceRule) -> int:
            return sum(1 for v in (r.scope_mtart, r.scope_plant_code, r.scope_stage_code) if v is not None)
        return max(candidates, key=_score)


def load_rules(db: Session) -> RuleIndex:
    rules = list(db.scalars(select(GovernanceRule)).all())
    return RuleIndex(_rules=rules)


# ---------------------------------------------------------------------------
# Preset index
# ---------------------------------------------------------------------------


@dataclass
class PresetIndex:
    _by_plant: Dict[str, MaterialPreset] = field(default_factory=dict)

    def match(self, plant_code: str) -> Optional[MaterialPreset]:
        return self._by_plant.get(plant_code)


def load_presets(db: Session) -> PresetIndex:
    from sqlalchemy.orm import joinedload
    presets = list(db.scalars(
        select(MaterialPreset).options(
            joinedload(MaterialPreset.plants),
            joinedload(MaterialPreset.fields),
        )
    ).unique().all())
    idx: Dict[str, MaterialPreset] = {}
    for p in presets:
        for plant in p.plants:
            idx[plant.plant_code] = p
    return PresetIndex(_by_plant=idx)


def sync_preset_fields_to_rules(db: Session, preset_index: PresetIndex) -> None:
    """Ensure each PresetField has a corresponding GovernanceRule for its plant."""
    for plant_code, preset in preset_index._by_plant.items():
        for pf in preset.fields:
            if not pf.allowed_values:
                continue
            allowed_list = json.loads(pf.allowed_values)
            if not allowed_list:
                continue
            # Find or create rule scoped to this plant + field
            rule = (
                db.query(GovernanceRule)
                .filter(
                    GovernanceRule.field_name == pf.field_name.upper(),
                    GovernanceRule.scope_plant_code == plant_code,
                    GovernanceRule.scope_mtart.is_(None),
                    GovernanceRule.scope_stage_code.is_(None),
                )
                .first()
            )
            csv_vals = ",".join(allowed_list)
            if rule is None:
                db.add(GovernanceRule(
                    field_name=pf.field_name.upper(),
                    scope_plant_code=plant_code,
                    allowed_values=csv_vals,
                    severity=pf.severity,
                ))
            else:
                rule.allowed_values = csv_vals
                rule.severity = pf.severity
    db.flush()


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

# The 20 MARC fields we track (lower-cased attribute names on Marc model)
MARC_FIELDS = [
    "mmsta", "dispr", "dismm", "dispo", "beskz", "sobsl", "ekgrp", "disgr",
    "eisbe", "minbe", "losfx", "plifz", "webaz", "lgpro", "lgfsb",
    "fhori", "schgt", "perkz", "mtvfp", "strgr",
]


@dataclass
class ViolationResult:
    field_name: str
    rule: GovernanceRule
    actual_value: Optional[str]
    expected_value: Optional[str]
    note: str


def evaluate_marc(
    marc: Marc,
    mtart: str,
    rule_index: RuleIndex,
) -> List[ViolationResult]:
    """Return list of violations for one MARC row."""
    violations: List[ViolationResult] = []
    stage = marc.mmsta or ""

    for attr in MARC_FIELDS:
        field_name = attr.upper()
        actual = getattr(marc, attr, None)
        actual_str = actual if actual is not None else ""

        rule = rule_index.match(field_name, mtart, marc.werks, stage)
        if rule is None:
            continue

        violated = False
        expected_display: Optional[str] = None
        note = ""

        if rule.allowed_values:
            allowed = [v.strip() for v in rule.allowed_values.split(",") if v.strip()]
            if actual_str not in allowed:
                violated = True
                expected_display = "/".join(allowed)
                note = (
                    f"{field_name}: expected one of [{expected_display}] "
                    f"for stage {stage} at plant {marc.werks}, got '{actual_str}'."
                )
        elif rule.expected_value is not None:
            if actual_str != rule.expected_value:
                violated = True
                expected_display = rule.expected_value
                note = (
                    f"{field_name}: expected '{rule.expected_value}' "
                    f"for stage {stage} at plant {marc.werks}, got '{actual_str}'."
                )

        if violated:
            violations.append(
                ViolationResult(
                    field_name=field_name,
                    rule=rule,
                    actual_value=actual_str or None,
                    expected_value=expected_display,
                    note=note,
                )
            )

    return violations


# ---------------------------------------------------------------------------
# Rebuild violations
# ---------------------------------------------------------------------------


def rebuild_violations(db: Session, rule_index: Optional[RuleIndex] = None) -> int:
    """Re-evaluate all MARC rows against rules. Returns total active violation count.

    Resolves violations that no longer apply; creates new ones.
    """
    # Sync preset fields into governance rules first so they are picked up by rule_index
    sync_preset_fields_to_rules(db, load_presets(db))

    if rule_index is None:
        rule_index = load_rules(db)

    now = datetime.utcnow()

    # Load all MARC rows with their material's mtart
    marc_rows: List[Marc] = list(db.scalars(select(Marc)).all())
    mtart_by_matnr: Dict[str, str] = {
        m.matnr: m.mtart
        for m in db.scalars(select(Material)).all()
    }

    # Build set of currently-violating keys
    active_keys: set[Tuple[str, str, str]] = set()

    for marc in marc_rows:
        mtart = mtart_by_matnr.get(marc.matnr, "")
        for v in evaluate_marc(marc, mtart, rule_index):
            active_keys.add((marc.matnr, marc.werks, v.field_name))

            # Upsert violation
            existing = (
                db.query(GovernanceViolation)
                .filter(
                    GovernanceViolation.matnr == marc.matnr,
                    GovernanceViolation.werks == marc.werks,
                    GovernanceViolation.field_name == v.field_name,
                    GovernanceViolation.resolved_at.is_(None),
                )
                .first()
            )
            if existing:
                existing.actual_value = v.actual_value
                existing.expected_value = v.expected_value
                existing.note = v.note
                existing.rule_id = v.rule.id
            else:
                db.add(
                    GovernanceViolation(
                        matnr=marc.matnr,
                        werks=marc.werks,
                        field_name=v.field_name,
                        rule_id=v.rule.id,
                        actual_value=v.actual_value,
                        expected_value=v.expected_value,
                        note=v.note,
                        detected_at=now,
                    )
                )

    # Resolve violations that no longer apply
    open_violations: List[GovernanceViolation] = list(
        db.scalars(
            select(GovernanceViolation).where(GovernanceViolation.resolved_at.is_(None))
        ).all()
    )
    for viol in open_violations:
        if (viol.matnr, viol.werks, viol.field_name) not in active_keys:
            viol.resolved_at = now

    db.flush()
    return len(active_keys)
