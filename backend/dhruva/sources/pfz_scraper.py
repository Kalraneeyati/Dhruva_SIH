"""INCOIS potential-fishing-zone advisories.

There is no API. INCOIS publishes PFZ daily for 586 landing centres across 14
sectors as human-readable bulletins, so this scrapes and attributes rather than
consuming a feed, and the architecture diagram must say so rather than implying
otherwise.

Two rules follow from being a guest on someone else's server. Nothing is fetched
twice inside the cache window, because their site is slow and a scraper that
re-fetches per query is abuse. And nothing is stored without `source_url` and
`fetched_at` — the schema makes source_url NOT NULL, so an unattributed PFZ line
cannot exist in the database.

The bulletin endpoint is configuration, not code: the public URL is not
discoverable from incois.gov.in and has to be confirmed with INCOIS. Everything
else here — fetching, parsing, caching, storing — is exercised by tests against
recorded bulletin text, so wiring a confirmed URL is a config change.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

import asyncpg
import httpx

USER_AGENT = "DHRUVA/0.1 (ISRO PS 26176 research prototype; contact via repository)"
DEFAULT_CACHE_HOURS = 12.0

# A bulletin line names a landing centre, then the zone as a bearing and distance
# from it, and usually a depth. Both "30 km" and "16 nm" appear in the wild, as do
# both "090 deg" and a compass word, so the parser takes each and normalises.
_BEARING_WORDS: dict[str, float] = {
    "N": 0,
    "NNE": 22.5,
    "NE": 45,
    "ENE": 67.5,
    "E": 90,
    "ESE": 112.5,
    "SE": 135,
    "SSE": 157.5,
    "S": 180,
    "SSW": 202.5,
    "SW": 225,
    "WSW": 247.5,
    "W": 270,
    "WNW": 292.5,
    "NW": 315,
    "NNW": 337.5,
}

# An entry starts at the beginning of the bulletin or after a sentence break, and
# runs until the next one starts. It is NOT line-anchored: bulletin entries wrap,
# and a line-anchored pattern loses whatever wrapped — typically the depth.
_ENTRY_ANCHOR = re.compile(
    r"(?:(?<=^)|(?<=[.;])|(?<=\n))\s*(?P<centre>[A-Z][A-Za-z .'\-]{2,40}?)\s*(?::|\s-\s)\s*"
)
_DISTANCE = re.compile(r"(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>km|kms|nm|nautical miles?)\b", re.I)
_BEARING_DEG = re.compile(r"(?P<val>\d{1,3}(?:\.\d+)?)\s*(?:deg(?:rees?)?|°)", re.I)
_BEARING_WORD = re.compile(r"\b(?:towards?|direction of)\s+(?P<w>[NSEW]{1,3})\b", re.I)
_DEPTH = re.compile(r"depth[^0-9]{0,12}(?P<val>\d+(?:\.\d+)?)\s*(?:m|metres?|meters?)\b", re.I)
_LATLON = re.compile(
    r"(?P<lat>\d{1,2}(?:\.\d+)?)\s*°?\s*(?P<ns>[NS])"
    r"[ ,/]+"
    r"(?P<lon>\d{1,3}(?:\.\d+)?)\s*°?\s*(?P<ew>[EW])",
    re.I,
)

KM_PER_NM = 1.852


@dataclass(slots=True)
class PfzRecord:
    """One advisory line. Attribution is not optional."""

    landing_centre: str
    source_url: str
    issued_for: dt.date
    bearing_deg: float | None = None
    distance_nm: float | None = None
    depth_m: float | None = None
    lat: float | None = None
    lon: float | None = None
    region: str | None = None
    raw: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_url:
            raise ValueError("a PFZ record without a source_url must not exist")


def parse_bulletin(
    text: str, *, source_url: str, issued_for: dt.date, region: str | None = None
) -> list[PfzRecord]:
    """Pull advisory lines out of bulletin text.

    Lines that name no zone at all are skipped rather than stored as a centre with
    empty fields: a PFZ row with no bearing and no position is indistinguishable
    from "no advisory today", and the two must not be confused.
    """
    plain = html.unescape(re.sub(r"<[^>]+>", " ", text))
    # Collapse wrapping so an entry is one run of text, then carve it into entries
    # by where the next landing centre is named.
    plain = re.sub(r"[ \t]*\n[ \t]*", "\n", plain)
    records: list[PfzRecord] = []

    anchors = list(_ENTRY_ANCHOR.finditer(plain))
    for i, m in enumerate(anchors):
        centre = " ".join(m.group("centre").split())
        end = anchors[i + 1].start() if i + 1 < len(anchors) else len(plain)
        body = " ".join(plain[m.end() : end].split())
        if len(body) < 8:
            continue

        rec = PfzRecord(
            landing_centre=centre,
            source_url=source_url,
            issued_for=issued_for,
            region=region,
            raw=body[:500],
        )

        if (d := _DISTANCE.search(body)) is not None:
            val = float(d.group("val"))
            unit = d.group("unit").lower()
            rec.distance_nm = val / KM_PER_NM if unit.startswith("km") else val

        if (b := _BEARING_DEG.search(body)) is not None:
            deg = float(b.group("val"))
            if 0 <= deg <= 360:
                rec.bearing_deg = deg % 360
        elif (w := _BEARING_WORD.search(body)) is not None:
            rec.bearing_deg = _BEARING_WORDS.get(w.group("w").upper())

        if (dep := _DEPTH.search(body)) is not None:
            rec.depth_m = float(dep.group("val"))

        if (ll := _LATLON.search(body)) is not None:
            lat = float(ll.group("lat")) * (-1 if ll.group("ns").upper() == "S" else 1)
            lon = float(ll.group("lon")) * (-1 if ll.group("ew").upper() == "W" else 1)
            rec.lat, rec.lon = lat, lon

        if rec.bearing_deg is None and rec.lat is None and rec.distance_nm is None:
            continue
        records.append(rec)

    return records


class PfzScraper:
    """Fetches and stores bulletins, and refuses to re-fetch inside the window."""

    def __init__(
        self,
        bulletin_url: str | None = None,
        *,
        cache_hours: float = DEFAULT_CACHE_HOURS,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.bulletin_url = bulletin_url
        self.cache_hours = cache_hours
        self._client = client
        self._last_fetch: dict[str, tuple[dt.datetime, str]] = {}

    async def fetch_bulletin(self, url: str | None = None, *, force: bool = False) -> str:
        target = url or self.bulletin_url
        if not target:
            raise ValueError(
                "no PFZ bulletin URL configured — it is not discoverable from "
                "incois.gov.in and must be confirmed with INCOIS"
            )

        cached = self._last_fetch.get(target)
        if cached and not force:
            stamped, body = cached
            if dt.datetime.now(dt.UTC) - stamped < dt.timedelta(hours=self.cache_hours):
                return body

        client = self._client or httpx.AsyncClient(
            timeout=60.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True
        )
        try:
            r = await client.get(target)
            r.raise_for_status()
            body = r.text
        finally:
            if self._client is None:
                await client.aclose()

        self._last_fetch[target] = (dt.datetime.now(dt.UTC), body)
        return body

    async def store(self, conn: asyncpg.Connection, records: list[PfzRecord]) -> int:
        now = dt.datetime.now(dt.UTC)
        written = 0
        for rec in records:
            await conn.execute(
                """
                INSERT INTO pfz_advisory
                    (issued_for, region, landing_centre, bearing_deg, distance_nm,
                     depth_m, source_url, fetched_at, raw, geom)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,
                        CASE WHEN $10::double precision IS NULL THEN NULL
                             ELSE ST_SetSRID(ST_MakePoint($11,$10), 4326) END)
                """,
                rec.issued_for,
                rec.region,
                rec.landing_centre,
                rec.bearing_deg,
                rec.distance_nm,
                rec.depth_m,
                rec.source_url,
                now,
                json.dumps(_jsonable(rec)),
                rec.lat,
                rec.lon,
            )
            written += 1
        return written


def _jsonable(rec: PfzRecord) -> dict[str, Any]:
    d = asdict(rec)
    d["issued_for"] = rec.issued_for.isoformat()
    return d
