"""API-facing (camelCase) response schemas, and `from_domain` converters.

Deliberately does NOT modify sources/base.py, sources/conditions.py, or
anything else already committed by the Phase 0-2 work — those stay exactly as
they are, snake_case internally, untouched. This module is the seam: it reads
Prateek's domain objects and produces the camelCase shapes
frontend/src/shared/types/domain.ts already expects, so his ongoing local
Phase 3 work never has to reconcile a wire-format change against this file.

Field names and nesting here are copy-checked against domain.ts, not
independently designed — see that file's own header comment for the same
claim in the other direction.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from dhruva.codec.codec import Capsule as CodecCapsule
from dhruva.evidence.schema import RiskVerdict
from dhruva.geo.local_boundaries import BoundaryDistance as LocalBoundaryDistance
from dhruva.sources.base import Observation
from dhruva.sources.conditions import Conditions

CAMEL = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ObservationOut(BaseModel):
    model_config = CAMEL

    variable: str
    value: float
    unit: str
    dataset_id: str
    upstream_dataset_id: str
    valid_time: dt.datetime
    cell_lat: float
    cell_lon: float
    requested_lat: float
    requested_lon: float
    grid_resolution_deg: float
    is_forecast: bool
    fetched_at: dt.datetime

    @classmethod
    def from_domain(cls, obs: Observation) -> "ObservationOut":
        return cls(
            variable=obs.variable.value,
            value=obs.value,
            unit=obs.unit,
            dataset_id=obs.dataset_id,
            upstream_dataset_id=obs.upstream_dataset_id,
            valid_time=obs.valid_time,
            cell_lat=obs.cell_lat,
            cell_lon=obs.cell_lon,
            requested_lat=obs.requested_lat,
            requested_lon=obs.requested_lon,
            grid_resolution_deg=obs.grid_resolution_deg,
            is_forecast=obs.is_forecast,
            fetched_at=obs.fetched_at,
        )


class ConditionsOut(BaseModel):
    model_config = CAMEL

    requested_lat: float
    requested_lon: float
    when: dt.datetime
    primary: dict[str, ObservationOut]
    cross_checks: list[ObservationOut]
    errors: list[str]
    elapsed_ms: float
    notice: str
    datasets_used: list[str]
    missing: list[str]
    disagreements: list[dict]

    @classmethod
    def from_domain(cls, c: Conditions) -> "ConditionsOut":
        return cls(
            requested_lat=c.requested_lat,
            requested_lon=c.requested_lon,
            when=c.when,
            primary={k.value: ObservationOut.from_domain(v) for k, v in c.primary.items()},
            cross_checks=[ObservationOut.from_domain(o) for o in c.cross_checks],
            errors=[e.error for e in c.errors],
            elapsed_ms=c.elapsed_ms,
            notice=c.notice,
            datasets_used=c.datasets_used,
            missing=[v.value for v in c.missing],
            disagreements=[
                {
                    "variable": d.variable.value,
                    "primary": ObservationOut.from_domain(d.primary).model_dump(by_alias=True, mode="json"),
                    "other": ObservationOut.from_domain(d.other).model_dump(by_alias=True, mode="json"),
                    "delta": d.delta,
                    "tolerance": d.tolerance,
                }
                for d in c.disagreements()
            ],
        )


class BoundaryDistanceOut(BaseModel):
    model_config = CAMEL

    name: str
    line_type: str
    territory1: str | None
    territory2: str | None
    distance_m: float
    distance_nm: float
    indicative: bool
    source_url: str | None

    @classmethod
    def from_domain(cls, b: LocalBoundaryDistance) -> "BoundaryDistanceOut":
        return cls(
            name=b.name, line_type=b.line_type, territory1=b.territory1, territory2=b.territory2,
            distance_m=b.distance_m, distance_nm=b.distance_nm, indicative=b.indicative, source_url=b.source_url,
        )


class PfzRecordOut(BaseModel):
    model_config = CAMEL

    landing_centre: str
    source_url: str
    issued_for: str
    bearing_deg: float | None
    distance_nm: float | None
    depth_m: float | None
    lat: float | None
    lon: float | None
    region: str | None
    confidence: str


class CapsuleOut(BaseModel):
    model_config = CAMEL

    msg_type: str
    schema_ver: int
    issue_slot: int
    valid_hours: int
    zone_id: int
    lat_offset: int
    lon_offset: int
    risk_class: str
    hazard_flags: list[str]
    wave_hs: float
    wind_kt: float
    wind_dir16: int
    curr_kt: float
    curr_dir16: int
    sst_c: float
    chl_class: str
    pfz_bearing16: int
    pfz_dist_nm: float
    pfz_confidence: int
    bnd_dist_nm: float
    bnd_type: str
    bnd_eta_min: float
    reason_code: int
    evidence_hash: str

    @classmethod
    def from_domain(cls, c: CodecCapsule) -> "CapsuleOut":
        return cls(**{f: getattr(c, f) for f in cls.model_fields})


class QueryTraceOut(BaseModel):
    model_config = CAMEL

    agent: str
    started_at: dt.datetime
    finished_at: dt.datetime
    ok: bool
    summary: str


class AdvisoryResponseOut(BaseModel):
    model_config = CAMEL

    query_text: str
    detected_language: str
    intent: str
    narrative: str
    verdict: RiskVerdict | None
    conditions: ConditionsOut | None
    pfz: list[PfzRecordOut]
    boundaries: list[BoundaryDistanceOut]
    route: list[dict] | None
    capsule: CapsuleOut | None
    trace: list[QueryTraceOut]
    firewall_retried: bool
    firewall_fell_back_to_template: bool
