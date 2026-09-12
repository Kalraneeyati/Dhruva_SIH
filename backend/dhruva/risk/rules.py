"""The risk engine — node 6.

Deterministic thresholds in, SAFE / CAUTION / NO-GO out, with the rule that fired.
No model is involved: a verdict a crew acts on must be reproducible from the
numbers and the table, and defensible line by line when a judge asks why.

Three properties this file exists to guarantee:

Absolute overrides run first and ignore everything favourable. A cyclone inside
300 km is NO-GO whatever the wave height says.

Missing data yields UNKNOWN, never SAFE. If wave height could not be fetched the
system does not know, and a system that answers "safe" when it does not know is
worse than one that answers nothing, because a crew acts on it.

The worst verdict wins. Any rule reaching NO-GO makes the whole answer NO-GO,
however many other rules are content — which is the same rule as "a favourable
fishing zone never renders above an active hazard".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dhruva.graph.state import BoatClass, DhruvaState, RiskClass, observation_for
from dhruva.risk.thresholds import (
    CYCLONE_RADIUS_KM,
    LIGHTNING_RADIUS_KM,
    PROVISIONAL,
    ClassThresholds,
    thresholds_for,
)
from dhruva.sources.registry import Variable

_SEVERITY: dict[RiskClass, int] = {
    RiskClass.SAFE: 0,
    RiskClass.UNKNOWN: 1,
    RiskClass.CAUTION: 2,
    RiskClass.NO_GO: 3,
}


@dataclass(frozen=True, slots=True)
class FiredRule:
    """Why the verdict is what it is."""

    rule_id: str
    verdict: RiskClass
    variable: str | None
    value: float | None
    threshold: float | None
    unit: str
    message: str


@dataclass(slots=True)
class RiskAssessment:
    risk_class: RiskClass
    fired: list[FiredRule] = field(default_factory=list)
    hazard_flags: list[str] = field(default_factory=list)
    provisional: bool = PROVISIONAL

    @property
    def rule_ids(self) -> list[str]:
        return [r.rule_id for r in self.fired]

    @property
    def deciding_rule(self) -> FiredRule | None:
        """The rule that set the verdict — the one the card should name."""
        for rule in self.fired:
            if rule.verdict is self.risk_class:
                return rule
        return None


def _worst(verdicts: list[RiskClass]) -> RiskClass:
    if not verdicts:
        return RiskClass.UNKNOWN
    return max(verdicts, key=lambda v: _SEVERITY[v])


def assess(
    state: DhruvaState,
    *,
    cyclone_distance_km: float | None = None,
    lightning_distance_km: float | None = None,
    tsunami_alert: bool = False,
) -> RiskAssessment:
    """Evaluate the table against whatever the fetch layer actually returned."""
    boat_class = state.get("boat_class") or BoatClass.FRP_UNDER_12M
    limits = thresholds_for(boat_class)

    fired: list[FiredRule] = []
    flags: list[str] = []

    # --- absolute overrides, before anything else ---------------------------
    if tsunami_alert:
        flags.append("tsunami")
        fired.append(
            FiredRule("TSUNAMI-A3", RiskClass.NO_GO, None, None, None, "", "Tsunami alert in force")
        )
    if cyclone_distance_km is not None and cyclone_distance_km <= CYCLONE_RADIUS_KM:
        flags.append("cyclone")
        fired.append(
            FiredRule(
                "CYCLONE-A1",
                RiskClass.NO_GO,
                "cyclone_distance",
                cyclone_distance_km,
                CYCLONE_RADIUS_KM,
                "km",
                f"Cyclone within {CYCLONE_RADIUS_KM:.0f} km",
            )
        )
    if lightning_distance_km is not None and lightning_distance_km <= LIGHTNING_RADIUS_KM:
        flags.append("lightning")
        fired.append(
            FiredRule(
                "LIGHTNING-A2",
                RiskClass.NO_GO,
                "lightning_distance",
                lightning_distance_km,
                LIGHTNING_RADIUS_KM,
                "km",
                f"Lightning within {LIGHTNING_RADIUS_KM:.0f} km",
            )
        )

    if any(r.verdict is RiskClass.NO_GO for r in fired):
        # An override is final. Evaluating the rest could only soften it, and the
        # message must name the hazard rather than the sea state.
        return RiskAssessment(RiskClass.NO_GO, fired, flags)

    # --- per-class thresholds -----------------------------------------------
    verdicts: list[RiskClass] = []
    for rule in (_wave_rule, _wind_rule):
        outcome = rule(state, limits)
        if outcome is not None:
            fired.append(outcome)
            verdicts.append(outcome.verdict)
            if outcome.verdict in (RiskClass.CAUTION, RiskClass.NO_GO) and outcome.variable:
                flags.append(outcome.variable.split("_")[0])

    return RiskAssessment(_worst(verdicts), fired, sorted(set(flags)))


def _wave_rule(state: DhruvaState, limits: ClassThresholds) -> FiredRule | None:
    obs = observation_for(state, Variable.WAVE_HEIGHT)
    if obs is None:
        return FiredRule(
            "DATA-U0",
            RiskClass.UNKNOWN,
            "wave_height",
            None,
            None,
            "m",
            "Wave height unavailable, so no verdict is possible",
        )
    if obs.value >= limits.no_go_wave_m:
        return FiredRule(
            "WAVE-N3",
            RiskClass.NO_GO,
            "wave_height",
            obs.value,
            limits.no_go_wave_m,
            "m",
            f"Wave height {obs.value:.2f} m at or above {limits.no_go_wave_m:.1f} m",
        )
    if obs.value >= limits.caution_wave_m:
        return FiredRule(
            "WAVE-C2",
            RiskClass.CAUTION,
            "wave_height",
            obs.value,
            limits.caution_wave_m,
            "m",
            f"Wave height {obs.value:.2f} m at or above {limits.caution_wave_m:.1f} m",
        )
    return FiredRule(
        "WAVE-S1",
        RiskClass.SAFE,
        "wave_height",
        obs.value,
        limits.caution_wave_m,
        "m",
        f"Wave height {obs.value:.2f} m below {limits.caution_wave_m:.1f} m",
    )


def _wind_rule(state: DhruvaState, limits: ClassThresholds) -> FiredRule | None:
    obs = observation_for(state, Variable.WIND_SPEED)
    if obs is None:
        return FiredRule(
            "DATA-U0",
            RiskClass.UNKNOWN,
            "wind_speed",
            None,
            None,
            "kt",
            "Wind speed unavailable, so no verdict is possible",
        )
    if obs.value >= limits.no_go_wind_kt:
        return FiredRule(
            "WIND-N3",
            RiskClass.NO_GO,
            "wind_speed",
            obs.value,
            limits.no_go_wind_kt,
            "kt",
            f"Wind {obs.value:.1f} kt at or above {limits.no_go_wind_kt:.0f} kt",
        )
    if obs.value >= limits.caution_wind_kt:
        return FiredRule(
            "WIND-C2",
            RiskClass.CAUTION,
            "wind_speed",
            obs.value,
            limits.caution_wind_kt,
            "kt",
            f"Wind {obs.value:.1f} kt at or above {limits.caution_wind_kt:.0f} kt",
        )
    return FiredRule(
        "WIND-S1",
        RiskClass.SAFE,
        "wind_speed",
        obs.value,
        limits.caution_wind_kt,
        "kt",
        f"Wind {obs.value:.1f} kt below {limits.caution_wind_kt:.0f} kt",
    )
