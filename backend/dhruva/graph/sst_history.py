"""Real historical SST trend, for the productivity_decline query.

The honest version of this handler (before this file existed) said outright
that a causal answer needs a chlorophyll time series this deployment doesn't
have credentials for (Copernicus). That's still true — chlorophyll is not
available here. But Open-Meteo Marine DOES serve real historical daily SST
(confirmed live against the API, going back to at least January of this
year, likely much further per the registry's coverage_start note), which
this deployment was NOT using. This module fetches it for real, computes a
real trend (not a guessed one), and the orchestrator's narrative states the
SST evidence plainly while continuing to refuse a causal productivity claim
chlorophyll data alone would be needed to support — upgrading the answer
from "no real data" to "one real, clearly-scoped signal," not overclaiming.

Does not touch sources/openmeteo.py for the same reason route_planner.py
doesn't: a historical date-range request is a different access pattern than
Prateek's adapter's point-in-time conditions_at design.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import httpx

MARINE_BASE = "https://marine-api.open-meteo.com/v1/marine"
LOOKBACK_WEEKS = 6


@dataclass(frozen=True, slots=True)
class SstTrendPoint:
    date: dt.date
    sst_c: float


@dataclass(frozen=True, slots=True)
class SstTrend:
    points: list[SstTrendPoint]
    first_week_avg_c: float
    last_week_avg_c: float
    change_c: float
    change_pct: float


def compute_trend(dates: list[str], values: list[float | None], *, weeks: int) -> SstTrend | None:
    """Pure — no network. Split out from fetch_sst_trend so the actual trend
    arithmetic is tested against fixed fixtures, not live weather."""
    points = [
        SstTrendPoint(date=dt.date.fromisoformat(d), sst_c=v)
        for d, v in zip(dates, values, strict=False)
        if v is not None
    ]
    if len(points) < 4:
        return None  # not enough real data to say anything about a trend

    window = max(1, len(points) // weeks)
    first_week = points[:window]
    last_week = points[-window:]
    first_avg = sum(p.sst_c for p in first_week) / len(first_week)
    last_avg = sum(p.sst_c for p in last_week) / len(last_week)
    change = last_avg - first_avg
    change_pct = (change / first_avg) * 100 if first_avg else 0.0

    return SstTrend(
        points=points,
        first_week_avg_c=first_avg,
        last_week_avg_c=last_avg,
        change_c=change,
        change_pct=change_pct,
    )


async def fetch_sst_trend(lat: float, lon: float, *, weeks: int = LOOKBACK_WEEKS, today: dt.date | None = None) -> SstTrend | None:
    """None only on a genuine fetch/parse failure — never a guessed trend."""
    today = today or dt.datetime.now(dt.UTC).date()
    start = today - dt.timedelta(weeks=weeks)
    params = {
        "latitude": f"{lat:.5f}",
        "longitude": f"{lon:.5f}",
        "daily": "sea_surface_temperature_mean",
        "start_date": start.isoformat(),
        "end_date": today.isoformat(),
        "timezone": "UTC",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(MARINE_BASE, params=params)
            r.raise_for_status()
            data = r.json()
        dates = data["daily"]["time"]
        values = data["daily"]["sea_surface_temperature_mean"]
    except (httpx.HTTPError, KeyError, ValueError):
        return None

    return compute_trend(dates, values, weeks=weeks)
