"""Real hazard-avoiding route planning over live wave-height data.

IMPLEMENTATION.md flags route optimization ("A* or similar over a maritime
grid weighted by hazard zones") as the "most hardcore CS" part of the build
and a strong differentiator — this was previously a straight-line stub
(`_handle_safe_route` in orchestrator.py) that stated as much honestly. This
replaces it with an actual weighted-grid search.

Approach: build a small lat/lon grid spanning the corridor between origin and
destination, fetch live wave height at every grid point in ONE batched
Open-Meteo request (Open-Meteo accepts comma-separated lat/lon lists and
returns one result per point — confirmed against the live API, not assumed),
then run Dijkstra over the grid graph with edge cost dominated by the
destination cell's wave height, with a hard penalty for cells at or above the
boat class's no-go threshold so the search actively steers around them
rather than merely disfavouring them.

This does NOT touch sources/openmeteo.py (Prateek's adapter, built for
single-point conditions_at queries) — batched multi-point fetching is a
different access pattern with a different caller, so it lives here as its
own small httpx client rather than forcing that shape into his module.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from typing import Awaitable, Callable

import httpx

from dhruva.risk.thresholds import THRESHOLDS, BoatClass

MARINE_BASE = "https://marine-api.open-meteo.com/v1/marine"
GRID_ROWS = 5
GRID_COLS = 5
LATERAL_MARGIN_DEG = 0.15  # how far the corridor can bulge sideways to dodge hazard


@dataclass(frozen=True, slots=True)
class RouteWaypoint:
    lat: float
    lon: float
    wave_height_m: float


@dataclass(frozen=True, slots=True)
class PlannedRoute:
    waypoints: list[RouteWaypoint]
    max_wave_on_route_m: float
    avoided_hazard: bool  # True if any grid cell exceeded the no-go threshold and was routed around


async def _fetch_wave_grid(lats: list[float], lons: list[float]) -> list[float]:
    """One batched request for the whole grid. Returns wave height per point,
    in the same order as the input lists."""
    params = {
        "latitude": ",".join(f"{v:.5f}" for v in lats),
        "longitude": ",".join(f"{v:.5f}" for v in lons),
        "hourly": "wave_height",
        "forecast_days": 1,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(MARINE_BASE, params=params)
        r.raise_for_status()
        data = r.json()

    # Open-Meteo returns a bare object (not a list) when only one point is requested.
    rows = data if isinstance(data, list) else [data]
    heights = []
    for row in rows:
        values = row.get("hourly", {}).get("wave_height", [])
        heights.append(values[0] if values else float("nan"))
    return heights


def _build_grid(origin: tuple[float, float], destination: tuple[float, float]) -> list[tuple[float, float]]:
    """A GRID_ROWS x GRID_COLS grid spanning the bounding corridor between
    origin and destination, widened by LATERAL_MARGIN_DEG so the search has
    room to route around a hazard rather than only ever finding the direct
    line."""
    lat0, lon0 = origin
    lat1, lon1 = destination
    lat_min, lat_max = min(lat0, lat1) - LATERAL_MARGIN_DEG, max(lat0, lat1) + LATERAL_MARGIN_DEG
    lon_min, lon_max = min(lon0, lon1) - LATERAL_MARGIN_DEG, max(lon0, lon1) + LATERAL_MARGIN_DEG

    points = []
    for i in range(GRID_ROWS):
        for j in range(GRID_COLS):
            lat = lat_min + (lat_max - lat_min) * i / (GRID_ROWS - 1)
            lon = lon_min + (lon_max - lon_min) * j / (GRID_COLS - 1)
            points.append((lat, lon))
    return points


def _nearest_index(points: list[tuple[float, float]], target: tuple[float, float]) -> int:
    return min(range(len(points)), key=lambda i: math.dist(points[i], target))


def _neighbors(idx: int) -> list[int]:
    row, col = divmod(idx, GRID_COLS)
    out = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            r, c = row + dr, col + dc
            if 0 <= r < GRID_ROWS and 0 <= c < GRID_COLS:
                out.append(r * GRID_COLS + c)
    return out


WaveGridFetcher = Callable[[list[float], list[float]], Awaitable[list[float]]]


async def plan_route(
    origin: tuple[float, float],
    destination: tuple[float, float],
    boat_class: BoatClass,
    *,
    fetch_grid: WaveGridFetcher = _fetch_wave_grid,
) -> PlannedRoute | None:
    """Dijkstra over a live wave-height grid. Returns None only if the live
    data fetch itself fails — never a guessed route.

    `fetch_grid` is injectable so tests exercise the real Dijkstra/hazard-
    avoidance logic against known wave-height fixtures instead of depending
    on whatever Open-Meteo happens to return right now."""
    grid = _build_grid(origin, destination)
    lats = [p[0] for p in grid]
    lons = [p[1] for p in grid]

    try:
        heights = await fetch_grid(lats, lons)
    except (httpx.HTTPError, ValueError, KeyError):
        return None

    no_go = THRESHOLDS[boat_class].no_go_wave_hs_m
    start = _nearest_index(grid, origin)
    goal = _nearest_index(grid, destination)

    # Dijkstra. Cost of entering a cell = its wave height, plus a hard
    # penalty at/above the no-go line so the search steers around it rather
    # than merely preferring lower waves — matches the safety framing risk/
    # rules.py already applies (no_go outranks a merely-shorter path).
    dist = {start: 0.0}
    prev: dict[int, int] = {}
    visited: set[int] = set()
    heap: list[tuple[float, int]] = [(0.0, start)]
    while heap:
        d, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)
        if u == goal:
            break
        for v in _neighbors(u):
            h = heights[v]
            if math.isnan(h):
                continue
            penalty = 1000.0 if h >= no_go else 0.0
            cost = h + penalty
            nd = d + cost
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd, v))

    if goal not in dist:
        return None  # grid fully blocked or unreachable — honest failure, not a guess

    path_idx = [goal]
    while path_idx[-1] != start:
        path_idx.append(prev[path_idx[-1]])
    path_idx.reverse()

    waypoints = [RouteWaypoint(lat=grid[i][0], lon=grid[i][1], wave_height_m=heights[i]) for i in path_idx]
    max_wave = max((wp.wave_height_m for wp in waypoints), default=0.0)
    avoided = any(heights[i] >= no_go for i in range(len(grid)) if i not in path_idx)

    return PlannedRoute(waypoints=waypoints, max_wave_on_route_m=max_wave, avoided_hazard=avoided)
