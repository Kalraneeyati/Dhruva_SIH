"""The graph's state object.

Everything else in phase 3 keys off this shape, so it comes first.

Nodes 2-5 (discovery, ocean, weather, geo) run in parallel and all write here.
LangGraph raises InvalidUpdateError when two concurrent nodes write the same key
without a reducer, and the failure only appears under fan-out — the graph looks
correct right up until it runs. So every key more than one node contributes to is
`Annotated[..., operator.add]`; keys a single node owns stay plain.
"""

from __future__ import annotations

import datetime as dt
import operator
from enum import StrEnum
from typing import Annotated, Any, TypedDict

from dhruva.sources.base import FetchError, Observation
from dhruva.sources.registry import Variable


class BoatClass(StrEnum):
    """Thresholds are per class: a 9 m FRP boat is not a 24 m trawler."""

    FRP_UNDER_12M = "frp_under_12m"
    MECHANISED_12_20M = "mechanised_12_20m"
    DEEP_SEA_OVER_20M = "deep_sea_over_20m"


class RiskClass(StrEnum):
    """Ordered by severity; the capsule stores this in 2 bits."""

    SAFE = "safe"
    CAUTION = "caution"
    NO_GO = "no_go"
    UNKNOWN = "unknown"


class Intent(StrEnum):
    """The eight question types in the problem statement. The planner classifies
    into these and the router maps each to a node set."""

    GO_NO_GO = "go_no_go"
    FISHING_ZONE = "fishing_zone"
    ROUTE = "route"
    BOUNDARY = "boundary"
    HAZARD = "hazard"
    CONDITIONS = "conditions"
    DECLINE_ATTRIBUTION = "decline_attribution"
    EXPLAIN = "explain"


class ToolPlan(TypedDict, total=False):
    """What the planner decided. It emits this and calls nothing itself — that
    separation is what keeps the run inspectable in Studio."""

    intent: Intent
    nodes: list[str]
    variables: list[Variable]
    needs_boundaries: bool
    needs_route: bool
    reason: str


class DhruvaState(TypedDict, total=False):
    # --- input, set once by the caller ---
    query: str
    language: str
    lat: float
    lon: float
    when: dt.datetime
    boat_class: BoatClass
    heading_deg: float | None
    speed_kt: float | None

    # --- planner (node 0) ---
    intent: Intent
    plan: ToolPlan

    # --- parallel fan-out (nodes 2-5): reducers are mandatory here ---
    observations: Annotated[list[Observation], operator.add]
    errors: Annotated[list[FetchError], operator.add]
    boundaries: Annotated[list[dict[str, Any]], operator.add]
    zones: Annotated[list[dict[str, Any]], operator.add]

    # --- risk (node 6): single writer, no reducer ---
    risk_class: RiskClass
    fired_rules: list[str]
    hazard_flags: list[str]

    # --- route (node 7) ---
    waypoints: list[tuple[float, float]]
    fuel_proxy: float | None

    # --- evidence (node 8) ---
    evidence: dict[str, Any]

    # --- narration, and what the firewall decided about it ---
    narration: str
    firewall_passed: bool
    firewall_violations: list[str]

    # --- codec (node 9) ---
    capsule_bits: str
    reason_code: int


def initial_state(
    query: str,
    lat: float,
    lon: float,
    *,
    when: dt.datetime | None = None,
    language: str = "en",
    boat_class: BoatClass = BoatClass.FRP_UNDER_12M,
    heading_deg: float | None = None,
    speed_kt: float | None = None,
) -> DhruvaState:
    """Seed a run.

    The accumulating keys are seeded empty so a node can append without first
    checking whether the key exists.
    """
    return DhruvaState(
        query=query,
        lat=lat,
        lon=lon,
        when=when or dt.datetime.now(dt.UTC),
        language=language,
        boat_class=boat_class,
        heading_deg=heading_deg,
        speed_kt=speed_kt,
        observations=[],
        errors=[],
        boundaries=[],
        zones=[],
        fired_rules=[],
        hazard_flags=[],
        firewall_violations=[],
    )


def observation_for(state: DhruvaState, variable: Variable) -> Observation | None:
    """First observation for a variable, or None.

    Nodes must go through this rather than indexing, because a variable with no
    live source is simply absent — and absent must never be read as zero.
    """
    for obs in state.get("observations", []):
        if obs.variable is variable:
            return obs
    return None
