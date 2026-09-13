"""Risk assessment — combines wave, wind and (when available) hazard bulletins
into one safe/caution/no-go verdict, per IMPLEMENTATION.md 3.2.

CLAUDE.md: "NO-GO outranks everything. A favourable fishing zone never
renders above an active hazard." This module only computes the verdict; the
frontend's render-order test (BoatApp.test.tsx) is what actually enforces the
outranking, but the ordering here — checking wave/wind severity and taking
the max — is the source of truth the frontend depends on being correct.

Cyclone/lightning/tsunami absolute overrides (CLAUDE.md) are wired to return
False today: IMPLEMENTATION.md flags that "a clean public API wasn't
confirmed" for IMD bulletins, and this module refuses to fabricate one. When
a real feed is wired in, `override_active`/`override_reason` are where it
plugs in — search for OVERRIDE_TODO.
"""

from __future__ import annotations

import datetime as dt

from dhruva.evidence.schema import EvidenceBundleEntry, HazardFlag, RiskClass, RiskFactor, RiskVerdict
from dhruva.risk.thresholds import THRESHOLDS, BoatClass
from dhruva.sources.conditions import Conditions
from dhruva.sources.registry import Variable

_SEVERITY_RANK = {RiskClass.SAFE: 0, RiskClass.CAUTION: 1, RiskClass.NO_GO: 2, RiskClass.UNKNOWN: 0}


def _worse(a: RiskClass, b: RiskClass) -> RiskClass:
    return a if _SEVERITY_RANK[a] >= _SEVERITY_RANK[b] else b


def assess_risk(
    conditions: Conditions,
    boat_class: BoatClass,
    *,
    now: dt.datetime | None = None,
) -> RiskVerdict:
    now = now or dt.datetime.now(dt.UTC)
    limits = THRESHOLDS[boat_class]
    factors: list[RiskFactor] = []
    overall = RiskClass.SAFE
    contributing_ages: list[float] = []

    wave = conditions.primary.get(Variable.WAVE_HEIGHT)
    if wave is not None:
        contributing_ages.append((now - _aware(wave.fetched_at)).total_seconds())
        if wave.value >= limits.no_go_wave_hs_m:
            severity = RiskClass.NO_GO
            narrative = f"Wave height {wave.value:.1f} m exceeds the {limits.no_go_wave_hs_m:.1f} m no-go line for this boat class."
        elif wave.value >= limits.caution_wave_hs_m:
            severity = RiskClass.CAUTION
            narrative = f"Wave height {wave.value:.1f} m is above the {limits.caution_wave_hs_m:.1f} m caution line for this boat class."
        else:
            severity = None
        if severity is not None:
            overall = _worse(overall, severity)
            factors.append(
                RiskFactor(
                    hazard=HazardFlag.WAVE,
                    rule_id=f"wave_hs_{severity.value}_{boat_class.value}",
                    severity=severity,
                    narrative=narrative,
                    evidence=[
                        EvidenceBundleEntry(
                            key="wave_height",
                            value=wave.value,
                            unit=wave.unit,
                            dataset_id=wave.dataset_id,
                            cell_lat=wave.cell_lat,
                            cell_lon=wave.cell_lon,
                            valid_time=wave.valid_time,
                            threshold=limits.no_go_wave_hs_m if severity is RiskClass.NO_GO else limits.caution_wave_hs_m,
                            rule_id=f"wave_hs_{severity.value}_{boat_class.value}",
                        )
                    ],
                )
            )

    wind = conditions.primary.get(Variable.WIND_SPEED)
    if wind is not None:
        contributing_ages.append((now - _aware(wind.fetched_at)).total_seconds())
        if wind.value >= limits.no_go_wind_kt:
            severity = RiskClass.NO_GO
            narrative = f"Wind {wind.value:.0f} kt exceeds the {limits.no_go_wind_kt:.0f} kt no-go line for this boat class."
        elif wind.value >= limits.caution_wind_kt:
            severity = RiskClass.CAUTION
            narrative = f"Wind {wind.value:.0f} kt is above the {limits.caution_wind_kt:.0f} kt caution line for this boat class."
        else:
            severity = None
        if severity is not None:
            overall = _worse(overall, severity)
            factors.append(
                RiskFactor(
                    hazard=HazardFlag.WIND,
                    rule_id=f"wind_kt_{severity.value}_{boat_class.value}",
                    severity=severity,
                    narrative=narrative,
                    evidence=[
                        EvidenceBundleEntry(
                            key="wind_speed",
                            value=wind.value,
                            unit=wind.unit,
                            dataset_id=wind.dataset_id,
                            cell_lat=wind.cell_lat,
                            cell_lon=wind.cell_lon,
                            valid_time=wind.valid_time,
                            threshold=limits.no_go_wind_kt if severity is RiskClass.NO_GO else limits.caution_wind_kt,
                            rule_id=f"wind_kt_{severity.value}_{boat_class.value}",
                        )
                    ],
                )
            )

    if not factors:
        overall = RiskClass.SAFE if (wave is not None or wind is not None) else RiskClass.UNKNOWN

    # OVERRIDE_TODO: cyclone (300km) / lightning (50km) / tsunami absolute
    # overrides wire in here once a live IMD/RSMC feed is confirmed reachable
    # (IMPLEMENTATION.md: "a clean public API wasn't confirmed... verify
    # specifically before building on it"). Never fabricate one meanwhile.
    override_active = False
    override_reason: str | None = None

    data_age = max(contributing_ages) if contributing_ages else 0.0

    return RiskVerdict(
        risk_class=overall,
        boat_class=boat_class.value,
        factors=factors,
        override_active=override_active,
        override_reason=override_reason,
        computed_at=now,
        data_age_seconds=data_age,
    )


def _aware(value: dt.datetime) -> dt.datetime:
    return value if value.tzinfo else value.replace(tzinfo=dt.UTC)
