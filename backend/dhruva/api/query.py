"""The real /query endpoint — Phase 3/4/5 meeting point.

This is what turns the frontend from "a well-built UI over mock fixtures"
into an actually-working system: `graph/orchestrator.py` fetches live
Open-Meteo data, runs it through the risk engine and the numeric firewall,
and this router just serializes the result via api/schemas.py's camelCase
converters — the exact shape frontend/src/shared/types/domain.ts expects.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from dhruva.api.schemas import AdvisoryResponseOut, BoundaryDistanceOut, CapsuleOut, ConditionsOut, PfzRecordOut, QueryTraceOut
from dhruva.graph.orchestrator import answer_query

router = APIRouter(tags=["query"])

# The exact 8 official query strings — identical to
# frontend/src/shared/api/mock.ts's EXAMPLE_QUERIES — so GET /query?intent=...
# (used by the "try it" deep links) classifies to the same intent the
# frontend already labelled it with, rather than re-deriving it.
OFFICIAL_QUERY_TEXT_BY_INTENT: dict[str, str] = {
    "nearest_pfz": "Where is the nearest Potential Fishing Zone (PFZ) today?",
    "safe_to_venture": "Is it safe to venture into the sea tomorrow morning?",
    "conditions_at_location": "What are the tide, weather, and sea conditions near my fishing location?",
    "hazard_alerts": "Are there any lightning or cyclone alerts in my area?",
    "chlorophyll_sst_zones": "Which regions show high chlorophyll concentration and favourable sea surface temperature?",
    "safe_route": "What is the safest route for a fishing vessel considering weather and sea-state conditions?",
    "productivity_decline": "Why has fish productivity declined in a particular coastal region?",
    "geofence_avoidance": "Which fishing zones should be avoided due to hazardous marine conditions or geofencing restrictions?",
}


@router.post("/query", response_model=AdvisoryResponseOut, response_model_by_alias=True)
async def post_query(body: dict) -> AdvisoryResponseOut:
    text = body.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="'text' is required")
    location = body.get("location") or {}
    result = await answer_query(
        text,
        lat=location.get("lat"),
        lon=location.get("lon"),
        boat_class=body.get("boatClass") or "frp_country_craft",
    )
    return _to_response(result)


@router.get("/query", response_model=AdvisoryResponseOut, response_model_by_alias=True)
async def get_query_by_intent(intent: str = Query(...)) -> AdvisoryResponseOut:
    text = OFFICIAL_QUERY_TEXT_BY_INTENT.get(intent)
    if text is None:
        raise HTTPException(status_code=404, detail=f"unknown intent {intent!r}")
    result = await answer_query(text)
    return _to_response(result)


def _to_response(result) -> AdvisoryResponseOut:
    return AdvisoryResponseOut(
        query_text=result.query_text,
        detected_language=result.detected_language,
        intent=result.intent.value,
        narrative=result.narrative,
        verdict=result.verdict,
        conditions=ConditionsOut.from_domain(result.conditions) if result.conditions else None,
        pfz=[PfzRecordOut(**p) for p in result.pfz],
        boundaries=[BoundaryDistanceOut.from_domain(b) for b in result.boundaries],
        route=result.route,
        capsule=CapsuleOut.from_domain(result.capsule) if result.capsule else None,
        trace=[
            QueryTraceOut(agent=t.agent, started_at=t.started_at, finished_at=t.finished_at or t.started_at, ok=t.ok, summary=t.summary)
            for t in result.trace
        ],
        firewall_retried=result.firewall_retried,
        firewall_fell_back_to_template=result.firewall_fell_back_to_template,
    )
