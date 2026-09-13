"""Tests the SST trend arithmetic against fixed fixtures (compute_trend is
pure), plus one live smoke test proving Open-Meteo's historical daily SST
endpoint actually returns real multi-week data — the capability this module
exists to use, previously unused in this codebase.
"""

from __future__ import annotations

import datetime as dt

import pytest

from dhruva.graph.sst_history import compute_trend, fetch_sst_trend

KOCHI = (9.9658, 76.2367)


def _daily_series(start: dt.date, values: list[float]) -> tuple[list[str], list[float]]:
    dates = [(start + dt.timedelta(days=i)).isoformat() for i in range(len(values))]
    return dates, values


def test_detects_a_real_warming_trend():
    start = dt.date(2026, 8, 1)
    # 42 days, warming from 27.0C to 29.0C.
    values = [27.0 + (2.0 * i / 41) for i in range(42)]
    dates, vals = _daily_series(start, values)
    trend = compute_trend(dates, vals, weeks=6)
    assert trend is not None
    assert trend.change_c > 0
    assert trend.last_week_avg_c > trend.first_week_avg_c


def test_detects_a_cooling_trend():
    start = dt.date(2026, 8, 1)
    values = [30.0 - (1.5 * i / 41) for i in range(42)]
    dates, vals = _daily_series(start, values)
    trend = compute_trend(dates, vals, weeks=6)
    assert trend is not None
    assert trend.change_c < 0


def test_flat_series_has_near_zero_change():
    start = dt.date(2026, 8, 1)
    values = [28.0 for _ in range(42)]
    dates, vals = _daily_series(start, values)
    trend = compute_trend(dates, vals, weeks=6)
    assert trend is not None
    assert trend.change_c == pytest.approx(0.0, abs=1e-9)


def test_returns_none_for_too_little_real_data_rather_than_guessing():
    dates, vals = _daily_series(dt.date(2026, 8, 1), [28.0, 28.1])
    assert compute_trend(dates, vals, weeks=6) is None


def test_skips_null_readings_from_the_provider_rather_than_crashing():
    start = dt.date(2026, 8, 1)
    values = [27.0, None, 27.5, 28.0, None, 28.5, 29.0, 29.2]
    dates = [(start + dt.timedelta(days=i)).isoformat() for i in range(len(values))]
    trend = compute_trend(dates, values, weeks=2)
    assert trend is not None
    assert len(trend.points) == 6  # the two Nones dropped, not coerced to 0


@pytest.mark.asyncio
async def test_live_open_meteo_historical_sst_is_real_and_multi_week():
    """Smoke test against the real API — this is the actual capability
    discovery this module is built on: Open-Meteo's marine endpoint serves
    real historical daily SST, which nothing in this codebase used before."""
    trend = await fetch_sst_trend(*KOCHI, weeks=6)
    assert trend is not None
    assert len(trend.points) >= 30  # ~6 weeks of daily data
    assert 15.0 < trend.first_week_avg_c < 35.0  # sane SST range, not a parsing artifact
    assert 15.0 < trend.last_week_avg_c < 35.0
