"""Boundary loading and distance queries.

The database tests need PostGIS with the layers loaded; they skip when it is not
reachable so CI without a stack stays green. What they pin is the stuff that
silently goes wrong in geospatial code: filtering that drops territory, distances
computed in the wrong units, and boundaries that could be presented as legal.
"""

import os

import asyncpg
import pytest

from dhruva.geo.boundaries import ZONE_LAYERS, BoundaryDistance, _float, _int

DSN = (
    f"postgresql://dhruva:{os.environ.get('POSTGRES_PASSWORD', '')}"
    f"@localhost:{os.environ.get('POSTGRES_HOST_PORT', '55432')}/dhruva"
)

# The plan's original demo coordinate, 11.05N/79.85E, is ashore: elevation 2 m,
# no maritime zone contains it. This is the corrected one.
DEMO_LAT, DEMO_LON = 11.05, 79.95


async def _conn() -> asyncpg.Connection | None:
    try:
        return await asyncpg.connect(DSN, timeout=5)
    except Exception:
        return None


needs_db = pytest.mark.skipif(
    not os.environ.get("POSTGRES_PASSWORD"), reason="no database configured"
)


class TestUnits:
    def test_metres_convert_to_nautical_miles(self):
        b = BoundaryDistance("x", "Treaty", "India", "Sri Lanka", 1852.0, True, None)
        assert b.distance_nm == pytest.approx(1.0)

    def test_a_realistic_imbl_distance(self):
        b = BoundaryDistance(
            "Sri Lanka - India", "Treaty", "India", "Sri Lanka", 95_940.0, True, None
        )
        assert b.distance_nm == pytest.approx(51.8, abs=0.1)


class TestCoercion:
    @pytest.mark.parametrize("value", [None, "", "abc", {}])
    def test_bad_numbers_become_none_rather_than_raising(self, value):
        assert _int(value) is None
        assert _float(value) is None

    def test_good_numbers_survive(self):
        assert _int("42") == 42
        assert _float("1.5") == pytest.approx(1.5)


class TestLayerCoverage:
    def test_every_maritime_belt_is_loaded_not_just_the_eez(self):
        """A boat 2 km offshore is inside the baseline and therefore not in the
        `eez` polygon at all. Loading only the EEZ leaves the most common case
        resolving to no zone."""
        assert set(ZONE_LAYERS.values()) == {
            "internal_waters",
            "eez",
            "territorial_sea_12nm",
            "contiguous_24nm",
        }


@needs_db
class TestAgainstDatabase:
    async def test_indian_eez_area_includes_andaman_and_nicobar(self):
        """Filtering on iso_ter1='IND' silently drops the Andaman and Nicobar
        record, whose iso_ter1 is null, losing 664,448 km2 without an error."""
        conn = await _conn()
        if conn is None:
            pytest.skip("database not reachable")
        try:
            km2 = await conn.fetchval(
                "SELECT SUM(ST_Area(geom::geography))/1e6 FROM maritime_zone WHERE zone_type='eez'"
            )
            if km2 is None:
                pytest.skip("zones not loaded")
            assert km2 == pytest.approx(2_323_948, rel=0.01)
        finally:
            await conn.close()

    async def test_the_imbl_is_present_as_a_treaty_line(self):
        """The drift warning is measured against this. If it is missing the
        headline safety feature has nothing to measure."""
        conn = await _conn()
        if conn is None:
            pytest.skip("database not reachable")
        try:
            n = await conn.fetchval(
                "SELECT count(*) FROM boundary_line "
                "WHERE line_type='Treaty' AND name ILIKE '%Sri Lanka%India%'"
            )
            if n is None:
                pytest.skip("boundaries not loaded")
            assert n >= 1
        finally:
            await conn.close()

    async def test_no_boundary_can_be_stored_as_authoritative(self):
        """CLAUDE.md: boundaries are indicative, never legal. The schema CHECKs
        it, so this must fail at the database rather than in review."""
        conn = await _conn()
        if conn is None:
            pytest.skip("database not reachable")
        try:
            with pytest.raises(asyncpg.PostgresError):
                await conn.execute("UPDATE boundary_line SET indicative = false")
        finally:
            await conn.close()

    async def test_distances_are_geodesic_metres_not_degrees(self):
        """A degree-based distance would return a number near 1, not near 95000."""
        conn = await _conn()
        if conn is None:
            pytest.skip("database not reachable")
        try:
            d = await conn.fetchval(
                "SELECT ST_Distance(geom::geography, "
                "ST_SetSRID(ST_MakePoint($2,$1),4326)::geography) FROM boundary_line "
                "WHERE line_type='Treaty' AND name ILIKE '%Sri Lanka%' "
                "ORDER BY 1 LIMIT 1",
                DEMO_LAT,
                DEMO_LON,
            )
            if d is None:
                pytest.skip("boundaries not loaded")
            assert d > 1000  # metres, so tens of thousands; degrees would be < 10
        finally:
            await conn.close()
