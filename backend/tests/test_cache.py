"""The cache exists to make Gate 2's 3 s warm target reachable. These tests pin
the two properties that decide whether it does: tile keying (so separate boats in
one patch of sea share an entry) and staleness (so a hit never serves yesterday's
forecast as now)."""

import datetime as dt

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from dhruva.sources.cache import FETCHED_AT_ATTR, CacheKey, ZarrCache

WHEN = dt.datetime(2026, 9, 12, 14, 30, tzinfo=dt.UTC)


def _grid() -> xr.Dataset:
    return xr.Dataset(
        {"sst": (("time", "lat", "lon"), np.random.rand(3, 4, 4).astype("float32"))},
        coords={
            "time": pd.date_range("2026-09-12", periods=3, freq="h"),
            "lat": np.linspace(11.0, 11.75, 4),
            "lon": np.linspace(79.0, 79.75, 4),
        },
    )


@pytest.fixture
def cache(tmp_path):
    return ZarrCache(root=tmp_path / "zc", default_ttl_hours=6.0)


class TestTileKeying:
    def test_two_points_in_one_tile_share_a_key(self):
        """The whole point. Boats 10 km apart must not each trigger a fetch."""
        a = CacheKey.for_point("copernicus_phy_hourly", 11.05, 79.85, WHEN, ["thetao"])
        b = CacheKey.for_point("copernicus_phy_hourly", 11.92, 79.11, WHEN, ["thetao"])
        assert a.digest == b.digest

    def test_points_in_different_tiles_do_not(self):
        a = CacheKey.for_point("d", 11.05, 79.85, WHEN, ["thetao"])
        b = CacheKey.for_point("d", 12.05, 79.85, WHEN, ["thetao"])
        assert a.digest != b.digest

    def test_the_tile_actually_contains_the_point_that_made_it(self):
        k = CacheKey.for_point("d", 11.05, 79.85, WHEN, ["thetao"])
        assert k.covers(11.05, 79.85)
        assert (k.lat_min, k.lat_max) == (11.0, 12.0)
        assert (k.lon_min, k.lon_max) == (79.0, 80.0)

    def test_variable_order_does_not_change_identity(self):
        a = CacheKey.for_point("d", 11.05, 79.85, WHEN, ["uo", "vo"])
        b = CacheKey.for_point("d", 11.05, 79.85, WHEN, ["vo", "uo"])
        assert a.digest == b.digest

    def test_a_different_variable_set_is_a_different_entry(self):
        a = CacheKey.for_point("d", 11.05, 79.85, WHEN, ["uo"])
        b = CacheKey.for_point("d", 11.05, 79.85, WHEN, ["uo", "vo"])
        assert a.digest != b.digest

    def test_times_in_the_same_window_share_a_key(self):
        a = CacheKey.for_point("d", 11.05, 79.85, WHEN, ["x"], window_hours=24)
        b = CacheKey.for_point(
            "d", 11.05, 79.85, WHEN + dt.timedelta(hours=6), ["x"], window_hours=24
        )
        assert a.digest == b.digest

    def test_negative_longitude_floors_downward_not_toward_zero(self):
        """int() truncation would put -0.5 in tile 0 and break the Arabian Sea's
        western edge. floor() is correct."""
        k = CacheKey.for_point("d", -0.5, -0.5, WHEN, ["x"])
        assert (k.lat_min, k.lat_max) == (-1.0, 0.0)
        assert k.covers(-0.5, -0.5)


class TestRoundTrip:
    def test_put_then_get_returns_the_data(self, cache):
        k = CacheKey.for_point("d", 11.05, 79.85, WHEN, ["sst"])
        ds = _grid()
        cache.put(k, ds)
        got = cache.get(k)
        assert got is not None
        assert np.allclose(got.sst.values, ds.sst.values)
        assert cache.stats.hits == 1

    def test_a_miss_returns_none_and_is_counted(self, cache):
        k = CacheKey.for_point("nothing-here", 11.05, 79.85, WHEN, ["sst"])
        assert cache.get(k) is None
        assert cache.stats.misses == 1

    def test_put_stamps_freshness(self, cache):
        k = CacheKey.for_point("d", 11.05, 79.85, WHEN, ["sst"])
        cache.put(k, _grid())
        got = cache.get(k)
        assert got is not None
        assert FETCHED_AT_ATTR in got.attrs
        age = ZarrCache.age_of(got)
        assert age is not None and age < dt.timedelta(minutes=1)


class TestStaleness:
    def test_an_entry_past_its_ttl_is_not_a_hit(self, cache):
        k = CacheKey.for_point("d", 11.05, 79.85, WHEN, ["sst"])
        cache.put(k, _grid())
        assert cache.get(k, ttl_hours=0.0) is None
        assert cache.stats.stale == 1

    def test_an_entry_with_no_stamp_is_never_trusted(self, cache):
        """Freshness comes from the attribute, not the filesystem. A store with no
        stamp has unknown age, and unknown age must not be served."""
        k = CacheKey.for_point("d", 11.05, 79.85, WHEN, ["sst"])
        _grid().to_zarr(cache.path_for(k), mode="w", consolidated=True)
        assert cache.get(k) is None

    def test_prune_drops_stale_entries(self, cache):
        k = CacheKey.for_point("d", 11.05, 79.85, WHEN, ["sst"])
        cache.put(k, _grid())
        assert len(cache.entries()) == 1
        assert cache.prune(older_than_hours=0.0) == 1
        assert cache.entries() == []

    def test_prune_keeps_fresh_entries(self, cache):
        k = CacheKey.for_point("d", 11.05, 79.85, WHEN, ["sst"])
        cache.put(k, _grid())
        assert cache.prune(older_than_hours=24.0) == 0
        assert len(cache.entries()) == 1


class TestResilience:
    def test_a_corrupt_store_is_a_miss_not_a_crash(self, cache):
        k = CacheKey.for_point("d", 11.05, 79.85, WHEN, ["sst"])
        path = cache.path_for(k)
        path.mkdir(parents=True)
        (path / "zarr.json").write_text("{ this is not valid zarr")
        assert cache.get(k) is None
        assert not path.exists()  # dropped, so the next call refetches cleanly

    def test_overwriting_an_entry_leaves_no_temp_directory(self, cache):
        k = CacheKey.for_point("d", 11.05, 79.85, WHEN, ["sst"])
        cache.put(k, _grid())
        cache.put(k, _grid())
        assert [p.name for p in cache.root.iterdir()] == [cache.path_for(k).name]

    def test_hit_rate_reports_zero_with_no_traffic(self, cache):
        assert cache.stats.hit_rate == 0.0
