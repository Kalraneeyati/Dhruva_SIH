"""Tests the PFZ gradient heuristic against a fake adapter with known SST
values, so the math is verified deterministically rather than against
whatever Open-Meteo happens to return today.
"""

from __future__ import annotations

import datetime as dt

import pytest

from dhruva.graph.pfz_estimator import SAMPLE_OFFSET_DEG, estimate_candidate_pfz
from dhruva.sources.base import FetchOutcome, Observation
from dhruva.sources.registry import DatasetEntry, Registry, SourceKind, SpatialExtent, TemporalExtent, Variable, VariableSpec

LAT, LON = 9.9658, 76.2367


def _entry() -> DatasetEntry:
    return DatasetEntry(
        id="fake_sst",
        title="Fake SST",
        source=SourceKind.OPEN_METEO,
        dataset_id="fake",
        endpoint="https://example.invalid",
        variables={Variable.SST: VariableSpec(native_name="sst", native_unit="degC", unit="degC")},
        spatial=SpatialExtent(lat_min=-90, lat_max=90, lon_min=-180, lon_max=180, grid_resolution_deg=0.1),
        temporal=TemporalExtent(coverage_start=dt.datetime(2020, 1, 1, tzinfo=dt.UTC), cadence="PT1H"),
    )


class FakeAdapter:
    """Cooler to the north, warmer everywhere else — the gradient should
    point due north (bearing 0)."""

    def __init__(self, sst_by_direction: dict[str, float]):
        self.sst_by_direction = sst_by_direction

    async def fetch(self, entry, variables, lat, lon, when) -> FetchOutcome:
        if lat > LAT + SAMPLE_OFFSET_DEG / 2:
            value = self.sst_by_direction["N"]
        elif lat < LAT - SAMPLE_OFFSET_DEG / 2:
            value = self.sst_by_direction["S"]
        elif lon > LON + SAMPLE_OFFSET_DEG / 2:
            value = self.sst_by_direction["E"]
        else:
            value = self.sst_by_direction["W"]
        return FetchOutcome(
            observations=[
                Observation(
                    variable=Variable.SST, value=value, unit="degC", dataset_id="fake_sst",
                    upstream_dataset_id="fake", valid_time=when, cell_lat=lat, cell_lon=lon,
                    requested_lat=lat, requested_lon=lon, grid_resolution_deg=0.1,
                    is_forecast=True, fetched_at=when,
                )
            ]
        )


@pytest.mark.asyncio
async def test_points_toward_the_coolest_neighbour():
    registry = Registry(datasets=[_entry()])
    adapters = {SourceKind.OPEN_METEO: FakeAdapter({"N": 26.0, "S": 29.0, "E": 29.0, "W": 29.0})}

    candidate = await estimate_candidate_pfz(LAT, LON, registry=registry, adapters=adapters)

    assert candidate is not None
    assert candidate.bearing_deg == pytest.approx(0.0, abs=1.0)  # due north
    assert candidate.disclosed_as_unofficial is True
    assert "open-meteo" in candidate.method.lower() or "sst" in candidate.method.lower()


@pytest.mark.asyncio
async def test_confidence_scales_with_gradient_strength():
    registry = Registry(datasets=[_entry()])

    weak = await estimate_candidate_pfz(
        LAT, LON, registry=registry,
        adapters={SourceKind.OPEN_METEO: FakeAdapter({"N": 28.8, "S": 29.0, "E": 29.0, "W": 29.0})},
    )
    strong = await estimate_candidate_pfz(
        LAT, LON, registry=registry,
        adapters={SourceKind.OPEN_METEO: FakeAdapter({"N": 25.0, "S": 29.0, "E": 29.0, "W": 29.0})},
    )

    assert weak is not None and strong is not None
    assert strong.confidence >= weak.confidence


@pytest.mark.asyncio
async def test_returns_none_rather_than_guessing_when_no_source_answers():
    registry = Registry(datasets=[_entry()])
    candidate = await estimate_candidate_pfz(LAT, LON, registry=registry, adapters={})
    assert candidate is None
