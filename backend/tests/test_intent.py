"""Classifies exactly the 8 official ISRO PS26176 example queries — the same
strings frontend/src/shared/api/mock.ts uses — into the right intent, since
these are the actual acceptance test for the whole system.
"""

from __future__ import annotations

import pytest

from dhruva.graph.intent import QueryIntent, classify_intent

OFFICIAL_QUERIES: list[tuple[str, QueryIntent]] = [
    ("Where is the nearest Potential Fishing Zone (PFZ) today?", QueryIntent.NEAREST_PFZ),
    ("Is it safe to venture into the sea tomorrow morning?", QueryIntent.SAFE_TO_VENTURE),
    ("What are the tide, weather, and sea conditions near my fishing location?", QueryIntent.CONDITIONS_AT_LOCATION),
    ("Are there any lightning or cyclone alerts in my area?", QueryIntent.HAZARD_ALERTS),
    (
        "Which regions show high chlorophyll concentration and favourable sea surface temperature?",
        QueryIntent.CHLOROPHYLL_SST_ZONES,
    ),
    (
        "What is the safest route for a fishing vessel considering weather and sea-state conditions?",
        QueryIntent.SAFE_ROUTE,
    ),
    ("Why has fish productivity declined in a particular coastal region?", QueryIntent.PRODUCTIVITY_DECLINE),
    (
        "Which fishing zones should be avoided due to hazardous marine conditions or geofencing restrictions?",
        QueryIntent.GEOFENCE_AVOIDANCE,
    ),
]


@pytest.mark.parametrize("query,expected", OFFICIAL_QUERIES, ids=[q for q, _ in OFFICIAL_QUERIES])
def test_classifies_every_official_query_correctly(query: str, expected: QueryIntent) -> None:
    assert classify_intent(query) == expected


def test_unrecognised_text_falls_back_to_conditions_rather_than_guessing_a_specific_intent():
    assert classify_intent("asdkfjaslkdfj random text") == QueryIntent.CONDITIONS_AT_LOCATION
