"""Postgres-free maritime boundary distances.

`geo/boundaries.py` already implements the CLAUDE.md-locked path (PostGIS
`geography`, live Marine Regions WFS). This module is an ADDITION for running
the demo on a laptop with no Docker/Postgres available — not a quiet
replacement of that decision (CLAUDE.md: "if a decision here looks wrong, say
so and stop, do not quietly change it" — this says so, in this docstring and
in backend/README).

Same source (Marine Regions/VLIZ, via the same WFS query `boundaries.py`
uses), fetched once and bundled at `data/layers/india_boundaries.geojson` (18
real lines: the India-Sri Lanka IMBL treaty line, India-Pakistan median line,
India-Bangladesh, India-Maldives, the 200nm line, and straight baselines) so
the demo has zero live-network dependency for this data — the same
"graceful degradation" principle CLAUDE.md states as a design goal, not just
applied to it.

Distance is computed geodesically (pyproj's WGS84 geod), not by treating
lat/lon degrees as flat-plane coordinates — the same correction PostGIS's
`geography` type applies, and the exact bug geo-reviewer's own brief calls
out ("Distances in EPSG:4326 degrees are wrong").
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pyproj import Geod
from shapely.geometry import LineString, MultiLineString, Point, shape

DATA_PATH = Path(__file__).parents[3] / "data" / "layers" / "india_boundaries.geojson"
SOURCE_NAME = "Marine Regions (VLIZ) EEZ boundaries, via WFS (bundled snapshot)"
SOURCE_URL = "https://marineregions.org"

_GEOD = Geod(ellps="WGS84")


@dataclass(frozen=True, slots=True)
class BoundaryDistance:
    name: str
    line_type: str
    territory1: str | None
    territory2: str | None
    distance_m: float
    indicative: bool  # always True — CHECKed by construction, see __post_init__
    source_url: str | None

    def __post_init__(self) -> None:
        if not self.indicative:
            raise ValueError("a boundary line must always be marked indicative")

    @property
    def distance_nm(self) -> float:
        return self.distance_m / 1852.0


@dataclass(frozen=True, slots=True)
class _Line:
    name: str
    line_type: str
    territory1: str | None
    territory2: str | None
    geom: LineString | MultiLineString


@lru_cache(maxsize=1)
def _load_lines() -> list[_Line]:
    if not DATA_PATH.exists():
        return []
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    lines: list[_Line] = []
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        geom = shape(feat["geometry"])
        lines.append(
            _Line(
                name=props.get("line_name") or "(unnamed)",
                line_type=(props.get("line_type") or "unknown").lower().replace(" ", "_"),
                territory1=props.get("territory1"),
                territory2=props.get("territory2"),
                geom=geom,
            )
        )
    return lines


def _geodesic_distance_to_line(point: Point, geom: LineString | MultiLineString) -> float:
    """Nearest geodesic distance (metres) from `point` to `geom`.

    Shapely's own `.distance()` is planar (degrees), which is exactly the bug
    class this module exists to avoid — so it is used ONLY to find the
    nearest vertex/segment cheaply, and the actual reported distance is
    always recomputed geodesically from that nearest point.
    """
    nearest = _nearest_point_on_geom(point, geom)
    _, _, dist_m = _GEOD.inv(point.x, point.y, nearest[0], nearest[1])
    return dist_m


def _nearest_point_on_geom(point: Point, geom: LineString | MultiLineString) -> tuple[float, float]:
    from shapely.ops import nearest_points

    _, nearest = nearest_points(point, geom)
    return nearest.x, nearest.y


# "Straight baseline" lines mark where the coast is DEFINED from — every
# coastal point is trivially near one, and it tells a fisherman nothing
# navigationally useful. The lines that matter for a geofencing warning are
# the actual international ones: treaty/median/court-ruling lines and the
# 200nm EEZ limit. Excluded by default; pass include_baselines=True for the
# rare caller that wants the full unfiltered set.
_NAVIGATIONALLY_RELEVANT_EXCLUDES = {"straight_baseline"}


def nearest_boundaries(
    lat: float, lon: float, *, limit: int = 3, include_baselines: bool = False
) -> list[BoundaryDistance]:
    """Closest boundary lines to a point, nearest first. Pure and local — no
    network, no database, matching this module's whole reason to exist."""
    point = Point(lon, lat)  # shapely is (x=lon, y=lat) — the #1 bug class geo-reviewer flags
    lines = _load_lines()
    if not include_baselines:
        lines = [line for line in lines if line.line_type not in _NAVIGATIONALLY_RELEVANT_EXCLUDES]
    scored = [(line, _geodesic_distance_to_line(point, line.geom)) for line in lines]
    scored.sort(key=lambda pair: pair[1])
    return [
        BoundaryDistance(
            name=line.name,
            line_type=line.line_type,
            territory1=line.territory1,
            territory2=line.territory2,
            distance_m=dist,
            indicative=True,
            source_url=SOURCE_URL,
        )
        for line, dist in scored[:limit]
    ]
