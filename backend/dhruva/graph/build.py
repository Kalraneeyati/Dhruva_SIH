"""The LangGraph state machine.

    query -> planner(0) -> [discovery(2) | ocean(3) | weather(4) | geo(5)]
                        -> risk(6) -> route(7) -> evidence(8) -> codec(9)

Language (node 1) wraps the graph rather than sitting in it, so everything here
runs in English.

The planner emits a tool plan and calls nothing itself. That separation is what
makes a run inspectable — in Studio you can see what was decided before anything
was fetched — and it is easy to collapse by accident.

Nodes 2-5 fan out in parallel and all write to `observations`, which is why that
key carries an operator.add reducer in state.py.
"""

from __future__ import annotations

import datetime as dt
import os
from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from dhruva.evidence.firewall import render_template, validate
from dhruva.evidence.schema import build_bundle
from dhruva.graph.state import BoatClass, DhruvaState, Intent, RiskClass, ToolPlan
from dhruva.risk.rules import assess
from dhruva.sources.conditions import DEFAULT_VARIABLES, conditions_at, default_adapters
from dhruva.sources.registry import Registry, Variable

# Which variables each intent actually needs. Fetching everything for every
# question wastes the latency budget the gate is measured against.
INTENT_VARIABLES: dict[Intent, tuple[Variable, ...]] = {
    Intent.GO_NO_GO: (Variable.WAVE_HEIGHT, Variable.WIND_SPEED, Variable.WIND_DIRECTION),
    Intent.FISHING_ZONE: (Variable.SST, Variable.CHLOROPHYLL, Variable.WAVE_HEIGHT),
    Intent.ROUTE: (
        Variable.WAVE_HEIGHT,
        Variable.WIND_SPEED,
        Variable.CURRENT_SPEED,
        Variable.CURRENT_DIRECTION,
    ),
    Intent.BOUNDARY: (Variable.CURRENT_SPEED, Variable.CURRENT_DIRECTION),
    Intent.HAZARD: (Variable.WAVE_HEIGHT, Variable.WIND_SPEED),
    Intent.CONDITIONS: DEFAULT_VARIABLES,
    Intent.DECLINE_ATTRIBUTION: (Variable.SST, Variable.CHLOROPHYLL),
    Intent.EXPLAIN: (),
}

_KEYWORDS: list[tuple[Intent, tuple[str, ...]]] = [
    (Intent.BOUNDARY, ("border", "boundary", "imbl", "line", "எல்லை")),
    (Intent.ROUTE, ("route", "way to", "navigate", "path")),
    (Intent.FISHING_ZONE, ("fish", "catch", "zone", "pfz", "மீன்")),
    (Intent.DECLINE_ATTRIBUTION, ("why", "declin", "fallen", "fewer", "less fish")),
    (Intent.HAZARD, ("cyclone", "storm", "warning", "lightning", "tsunami")),
    (Intent.GO_NO_GO, ("go out", "safe", "can i", "should i", "போகலாமா")),
    (Intent.CONDITIONS, ("weather", "wave", "wind", "condition", "sea")),
]


def classify(query: str) -> Intent:
    """Keyword routing, deliberately.

    A model belongs here eventually, but routing that a judge can read is worth
    more than routing that is merely clever, and this is the part the eval set
    measures. Swapping in Gemini 2.5 Flash later changes this function only.
    """
    text = query.lower()
    for intent, needles in _KEYWORDS:
        if any(n in text for n in needles):
            return intent
    return Intent.CONDITIONS


# ------------------------------------------------------------------ nodes ----


def _point(state: DhruvaState) -> tuple[float, float]:
    """lat/lon are not required keys on the TypedDict, so read them through here
    rather than indexing. A run without a position is a caller bug and should say
    so plainly rather than raising KeyError three nodes deep."""
    lat, lon = state.get("lat"), state.get("lon")
    if lat is None or lon is None:
        raise ValueError("state has no position; seed it with initial_state()")
    return lat, lon


def planner(state: DhruvaState) -> dict[str, Any]:
    """Node 0. Decides; does not fetch."""
    intent = classify(state.get("query", ""))
    variables = list(INTENT_VARIABLES.get(intent, DEFAULT_VARIABLES))
    plan = ToolPlan(
        intent=intent,
        nodes=["ocean", "weather", "geo"],
        variables=variables,
        needs_boundaries=intent in (Intent.BOUNDARY, Intent.ROUTE, Intent.GO_NO_GO),
        needs_route=intent is Intent.ROUTE,
        reason=f"keyword match on intent {intent.value}",
    )
    return {"intent": intent, "plan": plan}


async def _fetch(state: DhruvaState, wanted: tuple[Variable, ...]) -> dict[str, Any]:
    plan = state.get("plan") or {}
    planned: tuple[Variable, ...] = tuple(plan.get("variables") or DEFAULT_VARIABLES)
    variables = tuple(v for v in planned if v in wanted) or wanted
    registry = Registry.load(os.environ.get("DHRUVA_REGISTRY", "data/registry.yaml"))
    adapters = default_adapters(
        copernicus_username=os.environ.get("COPERNICUSMARINE_SERVICE_USERNAME"),
        copernicus_password=os.environ.get("COPERNICUSMARINE_SERVICE_PASSWORD"),
    )
    lat, lon = _point(state)
    result = await conditions_at(
        lat,
        lon,
        state.get("when"),
        registry=registry,
        adapters=adapters,
        variables=variables,
    )
    return {"observations": list(result.primary.values()), "errors": result.errors}


async def ocean(state: DhruvaState) -> dict[str, Any]:
    """Node 3. SST, chlorophyll, currents."""
    return await _fetch(
        state,
        (Variable.SST, Variable.CHLOROPHYLL, Variable.CURRENT_SPEED, Variable.CURRENT_DIRECTION),
    )


async def weather(state: DhruvaState) -> dict[str, Any]:
    """Node 4. Wind and waves."""
    return await _fetch(
        state,
        (Variable.WAVE_HEIGHT, Variable.WAVE_PERIOD, Variable.WIND_SPEED, Variable.WIND_DIRECTION),
    )


async def discovery(state: DhruvaState) -> dict[str, Any]:
    """Node 2. Which datasets can answer, recorded for the trace."""
    registry = Registry.load(os.environ.get("DHRUVA_REGISTRY", "data/registry.yaml"))
    when = state.get("when") or dt.datetime.now(dt.UTC)
    plan = state.get("plan") or {}
    lat, lon = _point(state)
    chosen = {
        v.value: [d.id for d in registry.candidates(v, lat, lon, when)]
        for v in (plan.get("variables") or DEFAULT_VARIABLES)
    }
    return {"zones": [{"kind": "dataset_plan", "datasets": chosen}]}


async def geo(state: DhruvaState) -> dict[str, Any]:
    """Node 5. Boundaries and zones. Degrades to empty rather than failing the
    run when no database is configured."""
    dsn = os.environ.get("DHRUVA_DSN")
    if not dsn:
        return {}
    import asyncpg

    from dhruva.geo.boundaries import nearest_boundaries, zones_containing

    try:
        conn = await asyncpg.connect(dsn, timeout=5)
    except Exception:
        return {}
    try:
        lat, lon = _point(state)
        near = await nearest_boundaries(conn, lat, lon, limit=3)
        zones = await zones_containing(conn, lat, lon)
    finally:
        await conn.close()
    return {
        "boundaries": [
            {
                "name": b.name,
                "line_type": b.line_type,
                "distance_nm": round(b.distance_nm, 2),
                "indicative": b.indicative,
            }
            for b in near
        ],
        "zones": [{"kind": "zone", **z} for z in zones],
    }


def risk(state: DhruvaState) -> dict[str, Any]:
    """Node 6. Deterministic verdict."""
    a = assess(state)
    return {
        "risk_class": a.risk_class,
        "fired_rules": a.rule_ids,
        "hazard_flags": a.hazard_flags,
    }


def route(state: DhruvaState) -> dict[str, Any]:
    """Node 7. A* over the cost grid lands here in a later phase; it is a
    declared stub rather than a silent no-op so the trace shows it ran."""
    plan = state.get("plan") or {}
    if not plan.get("needs_route"):
        return {}
    return {"waypoints": [], "fuel_proxy": None}


def evidence(state: DhruvaState) -> dict[str, Any]:
    """Node 8. Build the bundle, narrate, and refuse anything unvalidated."""
    a = assess(state)
    bundle = build_bundle(state.get("observations", []), a)

    # Until the model is wired, narration IS the template. That is the correct
    # failure mode anyway: the template is built from bundle rows, so it cannot
    # fail its own check.
    narration = render_template(bundle)
    check = validate(narration, bundle, language=state.get("language", "en"))
    if not check.passed:
        narration = render_template(bundle)

    return {
        "evidence": bundle.model_dump(mode="json"),
        "narration": narration,
        "firewall_passed": check.passed,
        "firewall_violations": check.messages,
    }


def codec(state: DhruvaState) -> dict[str, Any]:
    """Node 9. Capsule encoding arrives in phase 4; the reason code is chosen
    from the verdict so the field is populated end to end."""
    verdict = state.get("risk_class", RiskClass.UNKNOWN)
    reason = {RiskClass.SAFE: 1, RiskClass.CAUTION: 41, RiskClass.NO_GO: 90}.get(verdict, 0)
    return {"reason_code": reason}


# ------------------------------------------------------------------ graph ----


def build_graph() -> StateGraph:
    g = StateGraph(DhruvaState)
    g.add_node("planner", planner)
    g.add_node("discovery", discovery)
    g.add_node("ocean", ocean)
    g.add_node("weather", weather)
    g.add_node("geo", geo)
    g.add_node("risk", risk)
    g.add_node("route", route)
    g.add_node("evidence", evidence)
    g.add_node("codec", codec)

    g.add_edge(START, "planner")
    for node in ("discovery", "ocean", "weather", "geo"):
        g.add_edge("planner", node)  # fan out
        g.add_edge(node, "risk")  # fan in
    g.add_edge("risk", "route")
    g.add_edge("route", "evidence")
    g.add_edge("evidence", "codec")
    g.add_edge("codec", END)
    return g


graph = build_graph().compile()


async def arun(query: str, lat: float, lon: float, **kw: Any) -> DhruvaState:
    """Async entry point. Nodes 2-5 do network I/O, so the graph must be driven
    with ainvoke — invoke() raises "No synchronous function provided" on the
    first async node it reaches."""
    from dhruva.graph.state import initial_state

    boat = kw.pop("boat_class", BoatClass.FRP_UNDER_12M)
    result: Any = await graph.ainvoke(initial_state(query, lat, lon, boat_class=boat, **kw))
    return cast(DhruvaState, result)


def run(query: str, lat: float, lon: float, **kw: Any) -> DhruvaState:
    """Blocking wrapper for scripts. Not for use inside a running loop."""
    import asyncio

    return asyncio.run(arun(query, lat, lon, **kw))
