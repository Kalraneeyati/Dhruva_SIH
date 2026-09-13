"""Direct unit tests for the risk engine — IMPLEMENTATION.md 3.2's threshold
table, exercised at its exact boundaries, not just indirectly through a live
integration test that happens to land wherever today's weather lands.
"""

from __future__ import annotations

import datetime as dt

import pytest

from dhruva.risk.rules import assess_risk
from dhruva.risk.thresholds import THRESHOLDS, BoatClass
from dhruva.sources.base import Observation
from dhruva.sources.conditions import Conditions
from dhruva.sources.registry import Variable

NOW = dt.datetime.now(dt.UTC)


def _conditions(wave_m: float | None = None, wind_kt: float | None = None) -> Conditions:
    primary = {}
    if wave_m is not None:
        primary[Variable.WAVE_HEIGHT] = Observation(
            variable=Variable.WAVE_HEIGHT, value=wave_m, unit="m", dataset_id="test", upstream_dataset_id="test",
            valid_time=NOW, cell_lat=9.9, cell_lon=76.2, requested_lat=9.9, requested_lon=76.2,
            grid_resolution_deg=0.1, is_forecast=True, fetched_at=NOW,
        )
    if wind_kt is not None:
        primary[Variable.WIND_SPEED] = Observation(
            variable=Variable.WIND_SPEED, value=wind_kt, unit="kt", dataset_id="test", upstream_dataset_id="test",
            valid_time=NOW, cell_lat=9.9, cell_lon=76.2, requested_lat=9.9, requested_lon=76.2,
            grid_resolution_deg=0.1, is_forecast=True, fetched_at=NOW,
        )
    return Conditions(requested_lat=9.9, requested_lon=76.2, when=NOW, primary=primary)


@pytest.mark.parametrize("boat_class", list(BoatClass))
def test_calm_conditions_are_always_safe_regardless_of_boat_class(boat_class: BoatClass):
    verdict = assess_risk(_conditions(wave_m=0.3, wind_kt=5), boat_class)
    assert verdict.risk_class.value == "safe"
    assert verdict.factors == []


@pytest.mark.parametrize("boat_class", list(BoatClass))
def test_wave_height_exactly_at_the_caution_line_triggers_caution(boat_class: BoatClass):
    limit = THRESHOLDS[boat_class].caution_wave_hs_m
    verdict = assess_risk(_conditions(wave_m=limit, wind_kt=1), boat_class)
    assert verdict.risk_class.value == "caution"


@pytest.mark.parametrize("boat_class", list(BoatClass))
def test_wave_height_exactly_at_the_no_go_line_triggers_no_go(boat_class: BoatClass):
    limit = THRESHOLDS[boat_class].no_go_wave_hs_m
    verdict = assess_risk(_conditions(wave_m=limit, wind_kt=1), boat_class)
    assert verdict.risk_class.value == "no_go"


@pytest.mark.parametrize("boat_class", list(BoatClass))
def test_wind_speed_exactly_at_the_no_go_line_triggers_no_go(boat_class: BoatClass):
    limit = THRESHOLDS[boat_class].no_go_wind_kt
    verdict = assess_risk(_conditions(wave_m=0.1, wind_kt=limit), boat_class)
    assert verdict.risk_class.value == "no_go"


def test_a_bigger_boat_class_tolerates_conditions_a_smaller_one_cannot():
    wave = THRESHOLDS[BoatClass.FRP_COUNTRY_CRAFT].no_go_wave_hs_m
    small = assess_risk(_conditions(wave_m=wave, wind_kt=1), BoatClass.FRP_COUNTRY_CRAFT)
    big = assess_risk(_conditions(wave_m=wave, wind_kt=1), BoatClass.DEEP_SEA_20M_PLUS)
    assert small.risk_class.value == "no_go"
    assert big.risk_class.value in ("safe", "caution")


def test_overall_verdict_is_the_worse_of_wave_and_wind():
    limits = THRESHOLDS[BoatClass.FRP_COUNTRY_CRAFT]
    verdict = assess_risk(
        _conditions(wave_m=limits.caution_wave_hs_m, wind_kt=limits.no_go_wind_kt),
        BoatClass.FRP_COUNTRY_CRAFT,
    )
    assert verdict.risk_class.value == "no_go"
    assert len(verdict.factors) == 2


def test_missing_data_reports_unknown_rather_than_a_false_safe():
    verdict = assess_risk(_conditions(), BoatClass.FRP_COUNTRY_CRAFT)
    assert verdict.risk_class.value == "unknown"


def test_every_factor_carries_evidence_with_a_threshold():
    limits = THRESHOLDS[BoatClass.FRP_COUNTRY_CRAFT]
    verdict = assess_risk(_conditions(wave_m=limits.no_go_wave_hs_m + 1), BoatClass.FRP_COUNTRY_CRAFT)
    assert len(verdict.factors) == 1
    evidence = verdict.factors[0].evidence[0]
    assert evidence.threshold == limits.no_go_wave_hs_m
    assert evidence.dataset_id == "test"


def test_data_age_reflects_the_oldest_contributing_reading():
    old = dt.datetime.now(dt.UTC) - dt.timedelta(hours=2)
    conditions = _conditions(wave_m=0.5, wind_kt=5)
    conditions.primary[Variable.WAVE_HEIGHT] = conditions.primary[Variable.WAVE_HEIGHT].model_copy(update={"fetched_at": old})
    verdict = assess_risk(conditions, BoatClass.FRP_COUNTRY_CRAFT)
    assert verdict.data_age_seconds >= 7000  # ~2 hours, allowing test execution slack


def test_no_absolute_override_is_fabricated_without_a_live_feed():
    verdict = assess_risk(_conditions(wave_m=0.1, wind_kt=1), BoatClass.FRP_COUNTRY_CRAFT)
    assert verdict.override_active is False
    assert verdict.override_reason is None
