"""The evidence bundle — node 8.

Every claim the system makes has a row here: the value, its unit, the dataset it
came from, the grid cell that answered, the hour it is valid for, and where
relevant the threshold it was compared against and the rule that fired.

This is what the numeric firewall validates narration against, and what the UI
requires before it will render a figure. A number with no row here cannot be
shown anywhere, including the shore console.

Most of it already exists: an Observation carries value, unit, dataset_id, cell
and valid_time. This assembles those with the risk engine's rules rather than
redesigning them.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from dhruva.sources.base import Observation

if TYPE_CHECKING:
    from dhruva.risk.rules import RiskAssessment


class EvidenceItem(BaseModel):
    """One defensible number."""

    key: str
    value: float
    unit: str
    dataset_id: str
    upstream_dataset_id: str | None = None
    cell: str = Field(description="the grid cell that answered, not the one requested")
    cell_lat: float | None = None
    cell_lon: float | None = None
    offset_km: float | None = Field(
        default=None, description="how far the answering cell is from the point asked about"
    )
    valid_time: dt.datetime | None = None
    is_forecast: bool = False
    threshold: float | None = None
    rule_id: str | None = None

    @classmethod
    def from_observation(cls, obs: Observation) -> EvidenceItem:
        return cls(
            key=obs.variable.value,
            value=obs.value,
            unit=obs.unit,
            dataset_id=obs.dataset_id,
            upstream_dataset_id=obs.upstream_dataset_id,
            cell=f"{obs.cell_lat:.4f}N, {obs.cell_lon:.4f}E",
            cell_lat=obs.cell_lat,
            cell_lon=obs.cell_lon,
            offset_km=round(obs.offset_km, 2),
            valid_time=obs.valid_time,
            is_forecast=obs.is_forecast,
        )


class EvidenceBundle(BaseModel):
    """Everything a narration is allowed to say a number about."""

    items: list[EvidenceItem] = Field(default_factory=list)
    risk_class: str | None = None
    fired_rules: list[str] = Field(default_factory=list)
    provisional_thresholds: bool = True
    notice: str = "Advisory only. Follow official INCOIS and IMD warnings."
    built_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.UTC))

    def values(self) -> list[float]:
        """Every number the narration may contain, before derived conversions."""
        out = [i.value for i in self.items]
        out += [i.threshold for i in self.items if i.threshold is not None]
        return out

    def by_key(self, key: str) -> EvidenceItem | None:
        for item in self.items:
            if item.key == key:
                return item
        return None

    @property
    def digest(self) -> str:
        """Truncated hash for the capsule's 12-bit evidence_hash field.

        Computed over the values and their sources, so the same advisory hashes
        the same way and a tampered one does not.
        """
        payload = json.dumps(
            [
                [i.key, round(i.value, 4), i.unit, i.dataset_id, i.cell]
                for i in sorted(self.items, key=lambda x: x.key)
            ],
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_prompt_block(self) -> str:
        """What the model is shown. Deliberately terse and explicit: these are the
        only numbers it may use, and it is told so."""
        lines = ["EVIDENCE — you may not state any number that is not in this list:"]
        for i in self.items:
            bit = f"  {i.key} = {i.value:g} {i.unit} (source {i.dataset_id}, cell {i.cell}"
            if i.valid_time:
                bit += f", valid {i.valid_time:%Y-%m-%d %H:%M}Z"
            bit += ")"
            if i.threshold is not None:
                bit += f" [threshold {i.threshold:g} {i.unit}, rule {i.rule_id}]"
            lines.append(bit)
        if self.risk_class:
            lines.append(f"  verdict = {self.risk_class} (rules: {', '.join(self.fired_rules)})")
        return "\n".join(lines)


def build_bundle(
    observations: list[Observation],
    assessment: RiskAssessment | None = None,
    extra: dict[str, Any] | None = None,
) -> EvidenceBundle:
    """Assemble observations and fired rules into one bundle.

    A rule's threshold is attached to the item it was compared against, so the
    evidence card can show "2.4 m, caution at 2.0 m, rule WAVE-C2" as one row
    rather than as three unrelated facts.
    """
    bundle = EvidenceBundle(items=[EvidenceItem.from_observation(o) for o in observations])

    if assessment is not None:
        bundle.risk_class = assessment.risk_class.value
        bundle.fired_rules = assessment.rule_ids
        bundle.provisional_thresholds = assessment.provisional
        for rule in assessment.fired:
            if rule.variable is None:
                continue
            item = bundle.by_key(rule.variable)
            if item is not None and rule.threshold is not None:
                item.threshold = rule.threshold
                item.rule_id = rule.rule_id
            elif item is None and rule.value is not None:
                # An override such as cyclone distance has no observation behind
                # it, but the number is still quoted, so it still needs a row.
                bundle.items.append(
                    EvidenceItem(
                        key=rule.variable,
                        value=rule.value,
                        unit=rule.unit,
                        dataset_id="risk_engine",
                        cell="n/a",
                        threshold=rule.threshold,
                        rule_id=rule.rule_id,
                    )
                )

    for key, value in (extra or {}).items():
        if isinstance(value, int | float):
            bundle.items.append(
                EvidenceItem(key=key, value=float(value), unit="", dataset_id="derived", cell="n/a")
            )
    return bundle
