"""A live, honestly-labelled candidate-PFZ estimator.

CLAUDE.md: "PFZ has no API — it is scraped and attributed. Never imply a feed
exists." The INCOIS PFZ bulletin has no public API and no confirmed URL
(IMPLEMENTATION.md flags this explicitly), and the real satellite chlorophyll
source that would let ORCA compute a proper front-detection PFZ
(Copernicus BGC, `copernicus_bgc_pft` in the registry) needs credentials this
deployment does not have configured.

Rather than fabricate an "official" PFZ entry, this module computes a
*candidate* zone from live SST alone (Open-Meteo Marine, no key needed): it
samples SST at four points around the query location and points toward the
coolest neighbour — classic upwelling fronts (cooler, nutrient-rich water)
are where pelagic fish aggregate, which is the same oceanographic principle
real PFZ advisories use, just with one input signal instead of INCOIS's full
multi-satellite pipeline. Every response using this says so explicitly and
is never labelled as an official INCOIS bulletin.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from dhruva.sources.base import SourceAdapter
from dhruva.sources.registry import DatasetEntry, Registry, SourceKind, Variable

SAMPLE_OFFSET_DEG = 0.2
NOMINAL_CANDIDATE_DISTANCE_NM = 12.0
SST_GRADIENT_FOR_MAX_CONFIDENCE_C = 1.5  # a 1.5C spread across ~44km reads as a strong front


@dataclass(frozen=True, slots=True)
class PfzCandidate:
    lat: float
    lon: float
    bearing_deg: float
    distance_nm: float
    confidence: int  # 0-3, matches the capsule's pfz_confidence field
    method: str
    disclosed_as_unofficial: bool = True


async def estimate_candidate_pfz(
    lat: float, lon: float, *, registry: Registry, adapters: dict[SourceKind, SourceAdapter]
) -> PfzCandidate | None:
    """None if SST could not be sampled at enough neighbours to compute a
    gradient — the honest failure mode is "no candidate", never a guess."""
    import datetime as dt

    now = dt.datetime.now(dt.UTC)
    offsets = {"N": (SAMPLE_OFFSET_DEG, 0.0), "S": (-SAMPLE_OFFSET_DEG, 0.0), "E": (0.0, SAMPLE_OFFSET_DEG), "W": (0.0, -SAMPLE_OFFSET_DEG)}

    readings: dict[str, float] = {}
    for label, (dlat, dlon) in offsets.items():
        value = await _sample_sst(lat + dlat, lon + dlon, now, registry=registry, adapters=adapters)
        if value is not None:
            readings[label] = value

    if len(readings) < 2:
        return None

    coolest_label = min(readings, key=lambda k: readings[k])
    warmest = max(readings.values())
    coolest = readings[coolest_label]
    gradient = warmest - coolest

    dlat, dlon = offsets[coolest_label]
    bearing = (math.degrees(math.atan2(dlon, dlat)) + 360.0) % 360.0

    confidence = min(3, max(0, round(3 * min(gradient, SST_GRADIENT_FOR_MAX_CONFIDENCE_C) / SST_GRADIENT_FOR_MAX_CONFIDENCE_C)))

    target_lat, target_lon = _project(lat, lon, bearing, NOMINAL_CANDIDATE_DISTANCE_NM)

    return PfzCandidate(
        lat=target_lat,
        lon=target_lon,
        bearing_deg=bearing,
        distance_nm=NOMINAL_CANDIDATE_DISTANCE_NM,
        confidence=confidence,
        method=f"live SST gradient ({gradient:.2f}C across {SAMPLE_OFFSET_DEG * 111.32:.0f}km, Open-Meteo Marine)",
    )


async def _sample_sst(lat, lon, when, *, registry: Registry, adapters: dict[SourceKind, SourceAdapter]) -> float | None:
    candidates: list[DatasetEntry] = registry.candidates(Variable.SST, lat, lon, when)
    for entry in candidates:
        adapter = adapters.get(entry.source)
        if adapter is None:
            continue
        outcome = await adapter.fetch(entry, [Variable.SST], lat, lon, when)
        for obs in outcome.observations:
            if obs.variable is Variable.SST:
                return obs.value
    return None


def _project(lat: float, lon: float, bearing_deg: float, distance_nm: float) -> tuple[float, float]:
    """Destination point given a start, bearing and geodesic distance —
    small-distance flat-Earth approximation is fine at 12nm; a real route
    engine (graph/route.py, not built for this pass) would use pyproj's Geod
    for anything longer."""
    distance_km = distance_nm * 1.852
    bearing_rad = math.radians(bearing_deg)
    dlat = (distance_km * math.cos(bearing_rad)) / 111.32
    dlon = (distance_km * math.sin(bearing_rad)) / (111.32 * math.cos(math.radians(lat)))
    return lat + dlat, lon + dlon
