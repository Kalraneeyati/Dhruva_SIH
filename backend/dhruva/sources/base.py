"""What a fetch returns, and what every adapter must implement.

An `Observation` is a number that knows where it came from. It is deliberately
not a bare float: the numeric firewall in phase 3 validates narration against
these fields, and the UI refuses to render a figure without one.

`cell_lat`/`cell_lon` are the cell the provider *answered with*, which is not the
cell we asked for. Open-Meteo's marine and forecast endpoints returned two
different cells for one coordinate pair — 11.0417N/79.9584E and 11.0721N/79.7782E
for a request at 11.05N/79.85E. Quoting the requested position next to a value
that came from 12 km away is exactly the kind of untraceable number this project
exists to prevent.
"""

from __future__ import annotations

import datetime as dt
import math
from typing import Protocol

from pydantic import BaseModel, Field, field_validator

from dhruva.sources.registry import DatasetEntry, Variable


class Observation(BaseModel):
    """One value, with everything needed to defend it."""

    variable: Variable
    value: float

    unit: str
    dataset_id: str = Field(description="registry id, not the upstream id")
    upstream_dataset_id: str
    valid_time: dt.datetime = Field(description="the instant the value describes, UTC")
    cell_lat: float = Field(description="latitude the provider answered with")
    cell_lon: float = Field(description="longitude the provider answered with")
    requested_lat: float
    requested_lon: float
    grid_resolution_deg: float
    is_forecast: bool = False
    fetched_at: dt.datetime

    @field_validator("value")
    @classmethod
    def _must_be_finite(cls, v: float) -> float:
        """Ocean models fill land and out-of-domain cells with NaN. An Observation
        is a number a person will be shown and may act on, so a non-finite one is
        refused at construction — it must surface as a FetchError, never as a
        wave height reading "nan"."""
        if not math.isfinite(v):
            raise ValueError("value is not finite (land cell, or outside the model domain)")
        return v

    @property
    def offset_km(self) -> float:
        """How far the answering cell sits from the point asked about."""
        mean_lat = math.radians((self.cell_lat + self.requested_lat) / 2)
        dy = (self.cell_lat - self.requested_lat) * 111.32
        dx = (self.cell_lon - self.requested_lon) * 111.32 * math.cos(mean_lat)
        return math.hypot(dx, dy)


class FetchError(BaseModel):
    """A source that failed. Carried alongside results rather than raised, so one
    dead provider degrades the answer visibly instead of losing the whole call."""

    dataset_id: str
    variable: Variable | None = None
    error: str


class FetchOutcome(BaseModel):
    observations: list[Observation] = Field(default_factory=list)
    errors: list[FetchError] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


class SourceAdapter(Protocol):
    """One per provider. Returns canonical units; never raises for a remote
    failure — it reports it."""

    async def fetch(
        self,
        entry: DatasetEntry,
        variables: list[Variable],
        lat: float,
        lon: float,
        when: dt.datetime,
    ) -> FetchOutcome: ...


def unusable_reason(value: float) -> str | None:
    """Why this number must not be shown, or None if it is fine.

    Adapters call this before building an Observation so a land cell degrades into
    a recorded error instead of an exception.
    """
    if math.isnan(value):
        return "no data at this cell (land, or outside the model domain)"
    if math.isinf(value):
        return "value is infinite"
    return None


def uv_to_speed_direction(u: float, v: float) -> tuple[float, float]:
    """Vector components to speed and the compass bearing the flow sets *toward*.

    Oceanographic convention: a current with u>0, v=0 flows eastward and is
    reported as setting toward 090. This is the opposite of the meteorological
    wind convention, where a wind is named for where it comes *from* — mixing the
    two silently reverses every drift projection, so it is spelled out here.
    """
    speed = math.hypot(u, v)
    bearing = (math.degrees(math.atan2(u, v)) + 360.0) % 360.0
    return speed, bearing


def to_compass_16(bearing_deg: float) -> int:
    """Index into the 16-point compass. The capsule stores bearings this way, so
    demo values must already sit on this grid or the online and offline cards
    disagree on screen."""
    return int((bearing_deg % 360.0) / 22.5 + 0.5) % 16
