"""The registry's job is to stop a stale source being mistaken for a live one,
and to stop a longitude convention silently excluding the Bay of Bengal."""

import datetime as dt

import pytest
from pydantic import ValidationError

from dhruva.sources.registry import (
    AuthKind,
    Coverage,
    DatasetEntry,
    Registry,
    SourceKind,
    SpatialExtent,
    TemporalExtent,
    Variable,
    VariableSpec,
)

NOW = dt.datetime(2026, 9, 12, tzinfo=dt.UTC)
INDIAN_EEZ = SpatialExtent(lat_min=6, lat_max=24, lon_min=66, lon_max=94, grid_resolution_deg=0.05)


def _entry(**kw: object) -> DatasetEntry:
    base: dict[str, object] = dict(
        id="x",
        title="t",
        source=SourceKind.OPEN_METEO,
        dataset_id="d",
        endpoint="https://example.invalid",
        auth=AuthKind.NONE,
        variables={Variable.SST: VariableSpec(native_name="sst", native_unit="degC", unit="degC")},
        spatial=INDIAN_EEZ,
        temporal=TemporalExtent(
            coverage_start=dt.datetime(2020, 1, 1, tzinfo=dt.UTC), cadence="PT1H"
        ),
    )
    return DatasetEntry.model_validate(base | kw)


class TestCoverage:
    def test_open_ended_coverage_is_live(self):
        t = TemporalExtent(coverage_start=dt.datetime(2020, 1, 1, tzinfo=dt.UTC), cadence="P1D")
        assert t.coverage_at(NOW) is Coverage.LIVE

    def test_the_incois_trap_a_dataset_ending_in_2011_is_an_archive(self):
        """NOAA_AVHRR_AMSR_datasets looks live from its name. It ends 2011-10-04.
        Asking it for 'now' returns 2011 data with no error."""
        t = TemporalExtent(
            coverage_start=dt.datetime(2002, 6, 1, tzinfo=dt.UTC),
            coverage_end=dt.datetime(2011, 10, 4, tzinfo=dt.UTC),
            cadence="P1D",
        )
        assert t.coverage_at(NOW) is Coverage.ARCHIVE
        assert not _entry(temporal=t).is_live_at(NOW)

    def test_recently_ended_is_live_not_archive(self):
        t = TemporalExtent(
            coverage_start=dt.datetime(2020, 1, 1, tzinfo=dt.UTC),
            coverage_end=NOW - dt.timedelta(days=3),
            cadence="P1D",
        )
        assert t.coverage_at(NOW) is Coverage.LIVE

    def test_months_old_is_stale(self):
        t = TemporalExtent(
            coverage_start=dt.datetime(2020, 1, 1, tzinfo=dt.UTC),
            coverage_end=NOW - dt.timedelta(days=120),
            cadence="P1D",
        )
        assert t.coverage_at(NOW) is Coverage.STALE

    def test_naive_coverage_end_is_treated_as_utc(self):
        t = TemporalExtent(
            coverage_start=dt.datetime(2020, 1, 1, tzinfo=dt.UTC),
            coverage_end=dt.datetime(2011, 10, 4),  # no tzinfo
            cadence="P1D",
        )
        assert t.coverage_at(NOW) is Coverage.ARCHIVE


class TestSpatial:
    def test_nagapattinam_is_inside_the_indian_eez(self):
        assert INDIAN_EEZ.contains(11.05, 79.85)

    def test_arabian_sea_and_bay_of_bengal_both_covered(self):
        assert INDIAN_EEZ.contains(15.0, 68.0)
        assert INDIAN_EEZ.contains(15.0, 92.0)

    def test_outside_is_rejected(self):
        assert not INDIAN_EEZ.contains(11.05, 120.0)
        assert not INDIAN_EEZ.contains(-5.0, 79.85)

    def test_a_0_360_source_still_matches_a_negative_longitude(self):
        """Some ocean grids publish 0..360. A caller always passes -180..180."""
        s = SpatialExtent(
            lat_min=-30,
            lat_max=30,
            lon_min=0,
            lon_max=359.75,
            grid_resolution_deg=0.25,
            lon_convention="0..360",
        )
        assert s.contains(10.0, -10.0)  # -10 == 350

    def test_reversed_bounds_are_rejected(self):
        with pytest.raises(ValidationError):
            SpatialExtent(lat_min=24, lat_max=6, lon_min=66, lon_max=94, grid_resolution_deg=0.05)


class TestUnits:
    def test_kelvin_to_celsius_via_scale_and_offset(self):
        v = VariableSpec(
            native_name="analysed_sst", native_unit="K", unit="degC", scale=1.0, offset=-273.15
        )
        assert v.to_canonical(300.15) == pytest.approx(27.0)

    def test_metres_per_second_to_knots(self):
        v = VariableSpec(native_name="wind", native_unit="m/s", unit="kt", scale=1.943844)
        assert v.to_canonical(10.0) == pytest.approx(19.43844)


class TestRegistry:
    def test_duplicate_ids_are_rejected(self):
        with pytest.raises(ValidationError, match="duplicate dataset ids"):
            Registry(datasets=[_entry(id="dup"), _entry(id="dup")])

    def test_candidates_prefers_lower_latency_then_finer_grid(self):
        slow = _entry(id="slow", latency_hours=12)
        fast_coarse = _entry(
            id="fast_coarse",
            latency_hours=1,
            spatial=SpatialExtent(
                lat_min=6, lat_max=24, lon_min=66, lon_max=94, grid_resolution_deg=0.5
            ),
        )
        fast_fine = _entry(id="fast_fine", latency_hours=1)
        reg = Registry(datasets=[slow, fast_coarse, fast_fine])
        got = [d.id for d in reg.candidates(Variable.SST, 11.05, 79.85, NOW)]
        assert got == ["fast_fine", "fast_coarse", "slow"]

    def test_an_archive_is_never_a_candidate(self):
        archive = _entry(
            id="archive",
            temporal=TemporalExtent(
                coverage_start=dt.datetime(2002, 6, 1, tzinfo=dt.UTC),
                coverage_end=dt.datetime(2011, 10, 4, tzinfo=dt.UTC),
                cadence="P1D",
            ),
        )
        reg = Registry(datasets=[archive])
        assert reg.candidates(Variable.SST, 11.05, 79.85, NOW) == []

    def test_a_variable_the_source_lacks_is_never_a_candidate(self):
        reg = Registry(datasets=[_entry()])
        assert reg.candidates(Variable.CHLOROPHYLL, 11.05, 79.85, NOW) == []

    def test_by_id_raises_for_unknown(self):
        with pytest.raises(KeyError):
            Registry(datasets=[_entry(id="a")]).by_id("nope")
