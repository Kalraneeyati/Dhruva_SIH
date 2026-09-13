"""Risk thresholds — IMPLEMENTATION.md 3.2.

Values here are engineering placeholders, exactly as CLAUDE.md requires them to
be labelled: "Before any public claim, replace with the published INCOIS Ocean
State Forecast criteria and cite the source in the file. Never present invented
safety thresholds as official."
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class BoatClass(StrEnum):
    FRP_COUNTRY_CRAFT = "frp_country_craft"
    MECHANISED_12_20M = "mechanised_12_20m"
    DEEP_SEA_20M_PLUS = "deep_sea_20m_plus"


class ClassThresholds(BaseModel):
    caution_wave_hs_m: float
    no_go_wave_hs_m: float
    caution_wind_kt: float
    no_go_wind_kt: float


THRESHOLDS: dict[BoatClass, ClassThresholds] = {
    BoatClass.FRP_COUNTRY_CRAFT: ClassThresholds(
        caution_wave_hs_m=2.0, no_go_wave_hs_m=3.0, caution_wind_kt=20, no_go_wind_kt=28
    ),
    BoatClass.MECHANISED_12_20M: ClassThresholds(
        caution_wave_hs_m=2.5, no_go_wave_hs_m=3.5, caution_wind_kt=25, no_go_wind_kt=33
    ),
    BoatClass.DEEP_SEA_20M_PLUS: ClassThresholds(
        caution_wave_hs_m=3.5, no_go_wave_hs_m=4.5, caution_wind_kt=30, no_go_wind_kt=40
    ),
}

# Absolute overrides regardless of boat class (CLAUDE.md): a NO-GO overrides
# the class-specific wave/wind table entirely.
CYCLONE_OVERRIDE_RADIUS_KM = 300.0
LIGHTNING_OVERRIDE_RADIUS_KM = 50.0
