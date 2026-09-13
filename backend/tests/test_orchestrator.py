"""End-to-end orchestrator tests against real live Open-Meteo data.

These are integration tests (real network call, no mocking) by design: the
whole point of Phase 3 landing is that the frontend stops talking to
fixtures and starts talking to a system that fetches real numbers. The
specific regression this file exists to catch: every intent's narrative
mentioning a number that isn't in its own evidence bundle gets silently
rewritten to "Answer withheld..." by the numeric firewall — this happened
during development for nearest_pfz, safe_route and geofence_avoidance (each
forgot to attach evidence for a number it stated), and only showed up via
manual curl testing, not automated tests. It won't happen silently again.
"""

from __future__ import annotations

import pytest

from dhruva.api.query import OFFICIAL_QUERY_TEXT_BY_INTENT
from dhruva.graph.orchestrator import answer_query

KOCHI = (9.9658, 76.2367)


@pytest.mark.asyncio
@pytest.mark.parametrize("intent,text", OFFICIAL_QUERY_TEXT_BY_INTENT.items())
async def test_every_official_query_ships_a_real_answer_not_a_firewall_withdrawal(intent: str, text: str) -> None:
    result = await answer_query(text, lat=KOCHI[0], lon=KOCHI[1])
    assert result.intent.value == intent
    assert result.narrative, "narrative must not be empty"
    assert not result.firewall_fell_back_to_template, (
        f"intent={intent} narrative failed the numeric firewall: {result.narrative!r} "
        "— a number in the narrative has no matching EvidenceBundleEntry"
    )
    assert len(result.trace) >= 1


@pytest.mark.asyncio
async def test_safe_to_venture_produces_a_capsule():
    result = await answer_query(OFFICIAL_QUERY_TEXT_BY_INTENT["safe_to_venture"], lat=KOCHI[0], lon=KOCHI[1])
    assert result.capsule is not None
    assert result.verdict is not None


@pytest.mark.asyncio
async def test_geofence_avoidance_uses_real_bundled_boundary_data():
    result = await answer_query(OFFICIAL_QUERY_TEXT_BY_INTENT["geofence_avoidance"], lat=9.15, lon=79.45)
    assert len(result.boundaries) > 0
    assert result.boundaries[0].indicative is True
