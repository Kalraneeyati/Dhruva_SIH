"""Evidence bundle and risk verdict schemas.

Mirrors frontend/src/shared/types/domain.ts field-for-field (camelCase on the
wire, via `to_camel` aliasing) so the TypeScript client and this backend never
need a translation layer beyond JSON. This IS the numeric-firewall contract
CLAUDE.md section "The numeric firewall" describes: a number that reaches the
frontend without one of these wrapping it cannot exist, because
`AdvisoryResponse.narrative` is validated against exactly these bundles before
it is ever returned (see evidence/firewall.py).
"""

from __future__ import annotations

import datetime as dt
from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

CAMEL = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class RiskClass(StrEnum):
    SAFE = "safe"
    CAUTION = "caution"
    NO_GO = "no_go"
    UNKNOWN = "unknown"


class HazardFlag(StrEnum):
    WAVE = "wave"
    WIND = "wind"
    SQUALL = "squall"
    LIGHTNING = "lightning"
    CYCLONE = "cyclone"
    CURRENT = "current"
    FOG = "fog"
    TSUNAMI = "tsunami"


class EvidenceBundleEntry(BaseModel):
    model_config = CAMEL

    key: str
    value: float
    unit: str
    dataset_id: str
    cell_lat: float
    cell_lon: float
    valid_time: dt.datetime
    threshold: float | None = None
    rule_id: str | None = None


class RiskFactor(BaseModel):
    model_config = CAMEL

    hazard: HazardFlag
    rule_id: str
    severity: RiskClass
    narrative: str
    evidence: list[EvidenceBundleEntry]


class RiskVerdict(BaseModel):
    model_config = CAMEL

    risk_class: RiskClass
    boat_class: str
    factors: list[RiskFactor]
    override_active: bool
    override_reason: str | None
    computed_at: dt.datetime
    data_age_seconds: float
    advisory_notice: str = "Advisory only. Follow official INCOIS and IMD warnings."
