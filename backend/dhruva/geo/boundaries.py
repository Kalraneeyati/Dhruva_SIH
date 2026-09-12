"""Maritime boundaries: loading them, and asking how far away they are.

Source is Marine Regions (VLIZ) over WFS rather than their bulk download, which
sits behind a form. Everything loaded is flagged indicative — the schema CHECKs
it, so the flag cannot be dropped by a later import.

Distances use PostGIS `geography`, which is geodesic and returns metres. A
degree-based ST_Distance on EPSG:4326 would be wrong everywhere and wrong by a
different amount at every latitude, and "how far to the IMBL" is the number a
crew would act on.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import asyncpg
import httpx

WFS = "https://geo.vliz.be/geoserver/MarineRegions/wfs"
WFS_SOURCE_NAME = "Marine Regions (VLIZ) EEZ, via WFS"
SCHEMA_SQL = Path(__file__).with_name("schema.sql")

# India's EEZ and every boundary line it shares, including the India-Sri Lanka
# line the drift warning is measured against.
INDIA_ISO = "IND"


@dataclass(frozen=True, slots=True)
class BoundaryDistance:
    """How far a point sits from a boundary, and which one."""

    name: str
    line_type: str
    territory1: str | None
    territory2: str | None
    distance_m: float
    indicative: bool
    source_url: str | None

    @property
    def distance_nm(self) -> float:
        return self.distance_m / 1852.0


async def apply_schema(conn: asyncpg.Connection) -> None:
    await conn.execute(SCHEMA_SQL.read_text(encoding="utf-8"))


async def _wfs_geojson(
    client: httpx.AsyncClient, type_name: str, cql: str, *, limit: int = 500
) -> dict[str, Any]:
    r = await client.get(
        WFS,
        params={
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeName": type_name,
            "cql_filter": cql,
            "outputFormat": "application/json",
            "count": str(limit),
            "srsName": "EPSG:4326",
        },
    )
    r.raise_for_status()
    return r.json()


# Marine Regions publishes each maritime belt as its own layer, so "which zone am
# I in" needs all of them: a boat 2 km off Nagapattinam is inside the baseline and
# therefore NOT in the `eez` polygon at all.
ZONE_LAYERS: dict[str, str] = {
    "MarineRegions:eez_internal_waters": "internal_waters",
    "MarineRegions:eez": "eez",
    "MarineRegions:eez_12nm": "territorial_sea_12nm",
    "MarineRegions:eez_24nm": "contiguous_24nm",
}


async def load_zones(
    conn: asyncpg.Connection, client: httpx.AsyncClient, sovereign: str = "India"
) -> dict[str, int]:
    """Load every maritime belt for a sovereign. Returns rows per zone type."""
    counts: dict[str, int] = {}
    for layer, zone_type in ZONE_LAYERS.items():
        counts[zone_type] = await _load_zone_layer(conn, client, layer, zone_type, sovereign)
    return counts


async def _load_zone_layer(
    conn: asyncpg.Connection,
    client: httpx.AsyncClient,
    layer: str,
    zone_type: str,
    sovereign: str,
) -> int:
    """Filter on sovereign1, never on iso_ter1.

    The Andaman and Nicobar Islands EEZ record has a null iso_ter1, so an
    iso_ter1='IND' filter drops 664,448 km2 of Indian waters without erroring —
    sovereign1='India' returns both records and totals 2,323,948 km2.
    """
    data = await _wfs_geojson(client, layer, f"sovereign1='{sovereign}'")
    now = dt.datetime.now(dt.UTC)
    rows = 0
    for feat in data.get("features", []):
        p = feat.get("properties", {})
        await conn.execute(
            """
            INSERT INTO maritime_zone
                (mrgid, name, zone_type, territory, sovereign, iso_ter,
                 source_name, source_url, fetched_at, geom)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,
                    ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON($10), 4326)))
            ON CONFLICT (mrgid, zone_type) DO UPDATE
              SET geom = EXCLUDED.geom, fetched_at = EXCLUDED.fetched_at
            """,
            _int(p.get("mrgid")),
            p.get("geoname"),
            zone_type,
            p.get("territory1"),
            p.get("sovereign1"),
            p.get("iso_ter1"),
            WFS_SOURCE_NAME,
            p.get("url1"),
            now,
            _geom_json(feat),
        )
        rows += 1
    return rows


async def load_boundaries(
    conn: asyncpg.Connection, client: httpx.AsyncClient, territory: str = "India"
) -> int:
    """Load every EEZ boundary line touching a territory.

    Both territory1 and territory2 are matched: a shared line names the two
    parties in an arbitrary order, and filtering on one side alone silently drops
    roughly half of them — including, depending on the row, the IMBL itself.
    """
    cql = f"territory1='{territory}' OR territory2='{territory}'"
    data = await _wfs_geojson(client, "MarineRegions:eez_boundaries", cql)
    now = dt.datetime.now(dt.UTC)
    rows = 0
    for feat in data.get("features", []):
        p = feat.get("properties", {})
        await conn.execute(
            """
            INSERT INTO boundary_line
                (line_id, name, line_type, territory1, territory2, sovereign1, sovereign2,
                 length_km, source_name, source_url, doc_date, fetched_at, geom)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,
                    ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON($13), 4326)))
            ON CONFLICT (line_id) DO UPDATE
              SET geom = EXCLUDED.geom, fetched_at = EXCLUDED.fetched_at
            """,
            _int(p.get("line_id")),
            p.get("line_name"),
            p.get("line_type"),
            p.get("territory1"),
            p.get("territory2"),
            p.get("sovereign1"),
            p.get("sovereign2"),
            _float(p.get("length_km")),
            WFS_SOURCE_NAME,
            p.get("url1"),
            str(p.get("doc_date") or ""),
            now,
            _geom_json(feat),
        )
        rows += 1
    return rows


async def nearest_boundaries(
    conn: asyncpg.Connection, lat: float, lon: float, *, limit: int = 3
) -> list[BoundaryDistance]:
    """Closest boundary lines to a point, geodesic metres, nearest first.

    ORDER BY on the geography distance uses the GiST index, so this stays fast
    as more lines are loaded.
    """
    rows = await conn.fetch(
        """
        SELECT name, line_type, territory1, territory2, indicative, source_url,
               ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint($2,$1),4326)::geography) AS d
        FROM boundary_line
        ORDER BY geom::geography <-> ST_SetSRID(ST_MakePoint($2,$1),4326)::geography
        LIMIT $3
        """,
        lat,
        lon,
        limit,
    )
    return [
        BoundaryDistance(
            name=r["name"] or "(unnamed)",
            line_type=r["line_type"] or "unknown",
            territory1=r["territory1"],
            territory2=r["territory2"],
            distance_m=float(r["d"]),
            indicative=r["indicative"],
            source_url=r["source_url"],
        )
        for r in rows
    ]


async def zones_containing(
    conn: asyncpg.Connection, lat: float, lon: float
) -> list[dict[str, Any]]:
    """Which maritime zones a point falls inside."""
    rows = await conn.fetch(
        """
        SELECT name, zone_type, territory, sovereign, indicative, source_url
        FROM maritime_zone
        WHERE ST_Intersects(geom, ST_SetSRID(ST_MakePoint($2,$1), 4326))
        """,
        lat,
        lon,
    )
    return [dict(r) for r in rows]


def _geom_json(feat: dict[str, Any]) -> str:
    import json

    return json.dumps(feat["geometry"])


def _int(v: Any) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
