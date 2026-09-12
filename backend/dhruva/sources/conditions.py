"""`conditions_at` — Gate 2.

Answers "what is the sea doing at this point, at this time" from the registry,
with every figure carrying its source, its timestamp and the grid cell that
actually answered.

Three things it deliberately does not do. It does not invent a value: a variable
no source could supply is absent from the result and its failure is recorded,
because a missing number must never become a guessed one. It does not fetch per
variable: datasets are fetched once with every variable they can serve, so asking
for SST and both current components costs one Copernicus call rather than three.
And it does not throw away the second opinion: when two providers can answer, the
lower-latency one becomes primary and the other is kept as a cross-check, which
is how a model disagreement becomes visible instead of silent.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import time

from pydantic import BaseModel, Field

from dhruva.sources.base import FetchError, FetchOutcome, Observation, SourceAdapter
from dhruva.sources.registry import DatasetEntry, Registry, SourceKind, Variable

ADVISORY_NOTICE = "Advisory only. Follow official INCOIS and IMD warnings."

DEFAULT_VARIABLES: tuple[Variable, ...] = (
    Variable.WAVE_HEIGHT,
    Variable.WAVE_PERIOD,
    Variable.WIND_SPEED,
    Variable.WIND_DIRECTION,
    Variable.CURRENT_SPEED,
    Variable.CURRENT_DIRECTION,
    Variable.SST,
    Variable.CHLOROPHYLL,
)

# How far two sources may differ before the disagreement is worth surfacing.
# Units are the canonical ones in the registry.
DISAGREEMENT_TOLERANCE: dict[Variable, float] = {
    Variable.WAVE_HEIGHT: 0.5,
    Variable.WAVE_PERIOD: 2.0,
    Variable.WIND_SPEED: 5.0,
    Variable.WIND_DIRECTION: 45.0,
    Variable.CURRENT_SPEED: 0.5,
    Variable.CURRENT_DIRECTION: 45.0,
    Variable.SST: 1.0,
    Variable.CHLOROPHYLL: 0.5,
}


class Disagreement(BaseModel):
    variable: Variable
    primary: Observation
    other: Observation
    delta: float
    tolerance: float


class Conditions(BaseModel):
    """Everything known about one point at one time, with provenance."""

    requested_lat: float
    requested_lon: float
    when: dt.datetime
    primary: dict[Variable, Observation] = Field(default_factory=dict)
    cross_checks: list[Observation] = Field(default_factory=list)
    errors: list[FetchError] = Field(default_factory=list)
    elapsed_ms: float = 0.0
    notice: str = ADVISORY_NOTICE

    @property
    def datasets_used(self) -> list[str]:
        seen = {o.dataset_id for o in self.primary.values()} | {
            o.dataset_id for o in self.cross_checks
        }
        return sorted(seen)

    @property
    def missing(self) -> list[Variable]:
        return [v for v in DEFAULT_VARIABLES if v not in self.primary]

    def value(self, variable: Variable) -> float | None:
        obs = self.primary.get(variable)
        return obs.value if obs else None

    def disagreements(self, tolerance: dict[Variable, float] | None = None) -> list[Disagreement]:
        """Where a second provider differs enough to be worth saying out loud.

        Direction is compared the short way round the compass, so 350 and 010 are
        20 degrees apart rather than 340.
        """
        limits = tolerance or DISAGREEMENT_TOLERANCE
        found: list[Disagreement] = []
        for other in self.cross_checks:
            prim = self.primary.get(other.variable)
            if prim is None:
                continue
            limit = limits.get(other.variable)
            if limit is None:
                continue
            delta = _difference(other.variable, prim.value, other.value)
            if delta > limit:
                found.append(
                    Disagreement(
                        variable=other.variable,
                        primary=prim,
                        other=other,
                        delta=delta,
                        tolerance=limit,
                    )
                )
        return found


def _difference(variable: Variable, a: float, b: float) -> float:
    if variable in (Variable.WIND_DIRECTION, Variable.CURRENT_DIRECTION, Variable.WAVE_DIRECTION):
        return abs((a - b + 180.0) % 360.0 - 180.0)
    return abs(a - b)


def _plan(
    registry: Registry, variables: tuple[Variable, ...], lat: float, lon: float, when: dt.datetime
) -> tuple[
    dict[str, tuple[DatasetEntry, list[Variable]]], list[FetchError], dict[Variable, list[str]]
]:
    """Group the request by dataset, and record each variable's source preference.

    Returns (jobs keyed by dataset id, errors for unservable variables, ranking).
    """
    jobs: dict[str, tuple[DatasetEntry, list[Variable]]] = {}
    errors: list[FetchError] = []
    ranking: dict[Variable, list[str]] = {}

    for var in variables:
        candidates = registry.candidates(var, lat, lon, when)
        if not candidates:
            errors.append(
                FetchError(dataset_id="-", variable=var, error="no live source covers this point")
            )
            continue
        ranking[var] = [c.id for c in candidates]
        for entry in candidates:
            if entry.id not in jobs:
                jobs[entry.id] = (entry, [])
            jobs[entry.id][1].append(var)
    return jobs, errors, ranking


async def conditions_at(
    lat: float,
    lon: float,
    when: dt.datetime | None = None,
    *,
    registry: Registry,
    adapters: dict[SourceKind, SourceAdapter],
    variables: tuple[Variable, ...] = DEFAULT_VARIABLES,
) -> Conditions:
    """Fan out across every live source that covers the point, in parallel."""
    when = when or dt.datetime.now(dt.UTC)
    started = time.perf_counter()

    jobs, errors, ranking = _plan(registry, variables, lat, lon, when)

    async def run(entry: DatasetEntry, wanted: list[Variable]) -> FetchOutcome:
        adapter = adapters.get(entry.source)
        if adapter is None:
            return FetchOutcome(
                errors=[
                    FetchError(dataset_id=entry.id, error=f"no adapter for {entry.source.value}")
                ]
            )
        try:
            return await adapter.fetch(entry, wanted, lat, lon, when)
        except Exception as exc:
            # An adapter that raises is a bug, but it must not take the answer with it.
            return FetchOutcome(
                errors=[FetchError(dataset_id=entry.id, error=f"{type(exc).__name__}: {exc}")]
            )

    outcomes = await asyncio.gather(*(run(e, v) for e, v in jobs.values()))

    by_dataset: dict[str, list[Observation]] = {}
    for outcome in outcomes:
        errors.extend(outcome.errors)
        for obs in outcome.observations:
            by_dataset.setdefault(obs.dataset_id, []).append(obs)

    result = Conditions(requested_lat=lat, requested_lon=lon, when=when, errors=errors)

    for var, preference in ranking.items():
        got = [
            obs for dsid in preference for obs in by_dataset.get(dsid, []) if obs.variable is var
        ]
        if not got:
            continue
        result.primary[var] = got[0]
        result.cross_checks.extend(got[1:])

    result.elapsed_ms = (time.perf_counter() - started) * 1000
    return result


def default_adapters(
    *,
    copernicus_username: str | None = None,
    copernicus_password: str | None = None,
    cache_root: str = ".zarr_cache",
) -> dict[SourceKind, SourceAdapter]:
    from dhruva.sources.cache import ZarrCache
    from dhruva.sources.copernicus import CopernicusAdapter
    from dhruva.sources.openmeteo import OpenMeteoAdapter

    cache = ZarrCache(root=cache_root)
    return {
        SourceKind.OPEN_METEO: OpenMeteoAdapter(),
        SourceKind.COPERNICUS: CopernicusAdapter(
            cache, username=copernicus_username, password=copernicus_password
        ),
    }
