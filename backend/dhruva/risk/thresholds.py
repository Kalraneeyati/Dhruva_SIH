"""The threshold table, as data.

Values mirror docs/THRESHOLDS.md. They are engineering placeholders, not INCOIS
criteria — PROVISIONAL stays True until they are replaced with published Ocean
State Forecast values and each row is cited. Anything that renders a verdict to a
person should surface that flag rather than quietly presenting these as official.
"""

from __future__ import annotations

from dataclasses import dataclass

from dhruva.graph.state import BoatClass

PROVISIONAL = True
PROVISIONAL_NOTE = (
    "Thresholds are engineering placeholders, not INCOIS Ocean State Forecast "
    "criteria. See docs/THRESHOLDS.md."
)

ADVISORY_NOTICE = "Advisory only. Follow official INCOIS and IMD warnings."

# Absolute overrides, evaluated before the per-class table.
CYCLONE_RADIUS_KM = 300.0
LIGHTNING_RADIUS_KM = 50.0


@dataclass(frozen=True, slots=True)
class ClassThresholds:
    caution_wave_m: float
    no_go_wave_m: float
    caution_wind_kt: float
    no_go_wind_kt: float


THRESHOLDS: dict[BoatClass, ClassThresholds] = {
    BoatClass.FRP_UNDER_12M: ClassThresholds(2.0, 3.0, 20.0, 28.0),
    BoatClass.MECHANISED_12_20M: ClassThresholds(2.5, 3.5, 25.0, 33.0),
    BoatClass.DEEP_SEA_OVER_20M: ClassThresholds(3.5, 4.5, 30.0, 40.0),
}


def thresholds_for(boat_class: BoatClass) -> ClassThresholds:
    return THRESHOLDS[boat_class]
