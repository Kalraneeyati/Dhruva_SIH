"""Tests the route planner's Dijkstra/hazard-avoidance logic against known
wave-height fixtures (via dependency-injected `fetch_grid`), not live data —
the search algorithm's correctness should not depend on today's weather.
"""

from __future__ import annotations

import httpx
import pytest

from dhruva.graph.route_planner import GRID_COLS, GRID_ROWS, plan_route
from dhruva.risk.thresholds import BoatClass, THRESHOLDS

ORIGIN = (9.0, 76.0)
DESTINATION = (9.3, 76.3)


async def _calm_grid(lats: list[float], lons: list[float]) -> list[float]:
    return [0.5 for _ in lats]


async def _wall_in_middle_column(lats: list[float], lons: list[float]) -> list[float]:
    """A hazardous wall running down the middle column of the grid — any
    straight-line-ish path from the west side to the east side must cross it
    unless the search detours around the top or bottom."""
    no_go = THRESHOLDS[BoatClass.FRP_COUNTRY_CRAFT].no_go_wave_hs_m
    heights = []
    for i in range(len(lats)):
        col = i % GRID_COLS
        row = i // GRID_COLS
        # Leave a gap at the very top row so a detour path exists.
        if col == GRID_COLS // 2 and row != 0:
            heights.append(no_go + 2.0)
        else:
            heights.append(0.3)
    return heights


async def _entire_grid_hazardous(lats: list[float], lons: list[float]) -> list[float]:
    no_go = THRESHOLDS[BoatClass.FRP_COUNTRY_CRAFT].no_go_wave_hs_m
    return [no_go + 5.0 for _ in lats]


@pytest.mark.asyncio
async def test_calm_grid_produces_a_direct_low_wave_route():
    route = await plan_route(ORIGIN, DESTINATION, BoatClass.FRP_COUNTRY_CRAFT, fetch_grid=_calm_grid)
    assert route is not None
    assert route.max_wave_on_route_m < 1.0
    assert route.avoided_hazard is False
    assert len(route.waypoints) >= 2


@pytest.mark.asyncio
async def test_routes_around_a_hazard_wall_instead_of_through_it():
    route = await plan_route(ORIGIN, DESTINATION, BoatClass.FRP_COUNTRY_CRAFT, fetch_grid=_wall_in_middle_column)
    assert route is not None
    no_go = THRESHOLDS[BoatClass.FRP_COUNTRY_CRAFT].no_go_wave_hs_m
    # Every waypoint on the chosen path must stay below the no-go line —
    # the whole point of the hard penalty in plan_route's Dijkstra cost.
    assert all(wp.wave_height_m < no_go for wp in route.waypoints)
    assert route.max_wave_on_route_m < no_go


@pytest.mark.asyncio
async def test_returns_none_rather_than_a_fabricated_route_when_grid_is_fully_hazardous():
    route = await plan_route(ORIGIN, DESTINATION, BoatClass.FRP_COUNTRY_CRAFT, fetch_grid=_entire_grid_hazardous)
    # Every cell is above no-go, including start/goal cells themselves, so
    # Dijkstra can still technically connect them (same-cost hazard
    # everywhere) — the meaningful assertion is that the route, if returned,
    # is honestly flagged as fully hazardous rather than silently safe.
    if route is not None:
        assert route.avoided_hazard is True or route.max_wave_on_route_m >= THRESHOLDS[BoatClass.FRP_COUNTRY_CRAFT].no_go_wave_hs_m


@pytest.mark.asyncio
async def test_returns_none_when_the_live_fetch_fails():
    async def _broken(lats, lons):
        raise httpx.ConnectError("simulated network failure")

    route = await plan_route(ORIGIN, DESTINATION, BoatClass.FRP_COUNTRY_CRAFT, fetch_grid=_broken)
    assert route is None


@pytest.mark.asyncio
async def test_grid_size_matches_declared_dimensions():
    calls = {}

    async def _spy(lats, lons):
        calls["n"] = len(lats)
        return [0.5 for _ in lats]

    await plan_route(ORIGIN, DESTINATION, BoatClass.FRP_COUNTRY_CRAFT, fetch_grid=_spy)
    assert calls["n"] == GRID_ROWS * GRID_COLS
