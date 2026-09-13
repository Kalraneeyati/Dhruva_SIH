"""Intent classification over the 8 official PS26176 query types.

Keyword-based, not an LLM call — deliberately, since no LLM key is configured
yet (see graph/orchestrator.py's module docstring) and a deterministic
classifier is something this demo can rely on being right, every time,
tonight. Swapping in an LLM-based classifier later is additive: this stays as
the offline/no-key fallback path either way, per the same reasoning as
evidence/firewall.py's `render_template`.
"""

from __future__ import annotations

from enum import StrEnum


class QueryIntent(StrEnum):
    NEAREST_PFZ = "nearest_pfz"
    SAFE_TO_VENTURE = "safe_to_venture"
    CONDITIONS_AT_LOCATION = "conditions_at_location"
    HAZARD_ALERTS = "hazard_alerts"
    CHLOROPHYLL_SST_ZONES = "chlorophyll_sst_zones"
    SAFE_ROUTE = "safe_route"
    PRODUCTIVITY_DECLINE = "productivity_decline"
    GEOFENCE_AVOIDANCE = "geofence_avoidance"


# Ordered so a more specific rule (e.g. "productivity decline") is checked
# before a more general one that could also match (e.g. "chlorophyll").
_RULES: list[tuple[QueryIntent, list[str]]] = [
    (QueryIntent.PRODUCTIVITY_DECLINE, ["productivity", "declin", "why has fish"]),
    (QueryIntent.GEOFENCE_AVOIDANCE, ["avoid", "geofenc", "restricted", "should be avoided"]),
    (QueryIntent.SAFE_ROUTE, ["route", "safest way", "navigat"]),
    (QueryIntent.NEAREST_PFZ, ["pfz", "fishing zone", "potential fishing"]),
    (QueryIntent.HAZARD_ALERTS, ["lightning", "cyclone", "alert", "warning"]),
    (QueryIntent.CHLOROPHYLL_SST_ZONES, ["chlorophyll", "favourable sea surface", "favorable sea surface"]),
    (QueryIntent.SAFE_TO_VENTURE, ["safe to venture", "safe to go", "sail tomorrow", "venture into the sea"]),
    (QueryIntent.CONDITIONS_AT_LOCATION, ["tide", "weather", "sea condition", "conditions near"]),
]

DEFAULT_INTENT = QueryIntent.CONDITIONS_AT_LOCATION


def classify_intent(text: str) -> QueryIntent:
    lower = text.lower()
    for intent, keywords in _RULES:
        if any(kw in lower for kw in keywords):
            return intent
    return DEFAULT_INTENT
