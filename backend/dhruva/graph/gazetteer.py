"""A small Indian coastal-location gazetteer, so a query can name a place
instead of requiring raw lat/lon. Not exhaustive by design — extending it is
a one-line addition per port, not an architecture change.
"""

from __future__ import annotations

COASTAL_LOCATIONS: dict[str, tuple[float, float]] = {
    "kochi": (9.9658, 76.2367),
    "cochin": (9.9658, 76.2367),
    "chennai": (13.0827, 80.2707),
    "visakhapatnam": (17.6868, 83.2185),
    "vizag": (17.6868, 83.2185),
    "mumbai": (18.9750, 72.8258),
    "goa": (15.4909, 73.8278),
    "panaji": (15.4909, 73.8278),
    "mangalore": (12.9141, 74.8560),
    "mangaluru": (12.9141, 74.8560),
    "tuticorin": (8.7642, 78.1348),
    "thoothukudi": (8.7642, 78.1348),
    "kakinada": (16.9891, 82.2475),
    "paradip": (20.3167, 86.6167),
    "veraval": (20.9159, 70.3629),
    "porbandar": (21.6417, 69.6293),
    "digha": (21.6274, 87.5083),
    "puri": (19.8135, 85.8312),
    "ratnagiri": (16.9902, 73.3120),
    "alappuzha": (9.4981, 76.3388),
    "alleppey": (9.4981, 76.3388),
    "kanyakumari": (8.0883, 77.5385),
    "nagapattinam": (10.7672, 79.8449),
    "dhanushkodi": (9.1500, 79.4500),
    "rameswaram": (9.2876, 79.3129),
    "diu": (20.7144, 70.9874),
    "okha": (22.4707, 69.0782),
}

DEFAULT_LOCATION = COASTAL_LOCATIONS["kochi"]  # the demo's canonical default


def resolve_location(text: str) -> tuple[float, float] | None:
    """Case-insensitive substring match against the gazetteer. Returns None
    (never a guessed coordinate) if nothing named in `text` is known."""
    lower = text.lower()
    for name, coords in COASTAL_LOCATIONS.items():
        if name in lower:
            return coords
    return None
