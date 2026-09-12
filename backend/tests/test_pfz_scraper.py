"""PFZ bulletin parsing.

The bulletin text below is SYNTHETIC, written to match the shapes INCOIS
publishes in (bearing plus distance from a named landing centre, sometimes a
position, mixed km and nm, mixed degree and compass-word bearings). It is not a
recorded INCOIS bulletin. When a real one is obtained these fixtures should be
replaced with it — a parser tuned only to invented text proves nothing about the
real format.
"""

import datetime as dt

import httpx
import pytest

from dhruva.sources.pfz_scraper import PfzRecord, PfzScraper, parse_bulletin

URL = "https://example.invalid/pfz/tamilnadu.html"
DAY = dt.date(2026, 9, 12)

BULLETIN = """
North Tamil Nadu sector advisory valid for 12 September 2026.

Nagapattinam: PFZ is located at a distance of 30 km in the direction of 090 degrees
from the landing centre, depth 40 m.
Karaikal: zone at 16 nm towards NE from the landing centre, depth 55 metres.
Cuddalore: PFZ at 11.5 N, 80.2 E, depth 35 m.
Chennai: no advisory issued today.
Puducherry - zone at a distance of 22 km, direction of 135 deg, depth 60 m.
"""


def _of(records: list[PfzRecord], centre: str) -> PfzRecord:
    return next(r for r in records if r.landing_centre == centre)


class TestParsing:
    def test_bearing_and_distance_in_km_convert_to_nautical_miles(self):
        r = _of(parse_bulletin(BULLETIN, source_url=URL, issued_for=DAY), "Nagapattinam")
        assert r.bearing_deg == pytest.approx(90.0)
        assert r.distance_nm == pytest.approx(30 / 1.852, abs=0.01)
        assert r.depth_m == pytest.approx(40.0)

    def test_a_distance_already_in_nm_is_not_converted(self):
        r = _of(parse_bulletin(BULLETIN, source_url=URL, issued_for=DAY), "Karaikal")
        assert r.distance_nm == pytest.approx(16.0)

    def test_a_compass_word_bearing_becomes_degrees(self):
        r = _of(parse_bulletin(BULLETIN, source_url=URL, issued_for=DAY), "Karaikal")
        assert r.bearing_deg == pytest.approx(45.0)

    def test_an_explicit_position_is_captured(self):
        r = _of(parse_bulletin(BULLETIN, source_url=URL, issued_for=DAY), "Cuddalore")
        assert (r.lat, r.lon) == (pytest.approx(11.5), pytest.approx(80.2))

    def test_a_dash_separator_parses_like_a_colon(self):
        r = _of(parse_bulletin(BULLETIN, source_url=URL, issued_for=DAY), "Puducherry")
        assert r.bearing_deg == pytest.approx(135.0)
        assert r.depth_m == pytest.approx(60.0)

    def test_a_centre_with_no_zone_is_skipped_not_stored_empty(self):
        """ "No advisory today" and "advisory with missing fields" must not look
        the same in the database."""
        centres = {
            r.landing_centre for r in parse_bulletin(BULLETIN, source_url=URL, issued_for=DAY)
        }
        assert "Chennai" not in centres

    def test_html_tags_and_entities_are_stripped(self):
        text = "<p>Nagapattinam: zone at 10 km, direction of 090 degrees, depth 30 m.</p>"
        r = parse_bulletin(text, source_url=URL, issued_for=DAY)[0]
        assert r.landing_centre == "Nagapattinam"
        assert r.bearing_deg == pytest.approx(90.0)

    def test_every_record_carries_its_source_and_date(self):
        for r in parse_bulletin(BULLETIN, source_url=URL, issued_for=DAY):
            assert r.source_url == URL
            assert r.issued_for == DAY


class TestAttribution:
    def test_a_record_without_a_source_cannot_be_constructed(self):
        """PFZ is scraped, so attribution is the whole basis for showing it."""
        with pytest.raises(ValueError, match="source_url"):
            PfzRecord(landing_centre="X", source_url="", issued_for=DAY)


class TestPoliteness:
    async def test_a_second_call_inside_the_window_does_not_refetch(self):
        """Their site is slow and we are guests; one fetch per window."""
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(200, text=BULLETIN)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        scraper = PfzScraper(URL, cache_hours=12, client=client)
        await scraper.fetch_bulletin()
        await scraper.fetch_bulletin()
        await client.aclose()
        assert calls["n"] == 1

    async def test_force_overrides_the_cache(self):
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(200, text=BULLETIN)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        scraper = PfzScraper(URL, cache_hours=12, client=client)
        await scraper.fetch_bulletin()
        await scraper.fetch_bulletin(force=True)
        await client.aclose()
        assert calls["n"] == 2

    async def test_no_configured_url_fails_loudly(self):
        """Better a clear error than a scraper quietly pointed at nothing."""
        with pytest.raises(ValueError, match="not discoverable"):
            await PfzScraper().fetch_bulletin()
