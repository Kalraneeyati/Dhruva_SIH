"""The source registry.

`data/registry.yaml` is the catalogue; this module is its schema and loader. The
discovery node reads the registry at runtime, so adding a dataset is a YAML edit
and never a code change.

Two fields exist because of things that actually bit us:

`coverage_end` — INCOIS's Daily-OI SST dataset looks live from its name and stops
in 2011. A dataset with a coverage_end in the past is an archive; asking it for
"now" silently returns the last thing it has. `is_live_at()` is the guard.

`grid_resolution_deg` — Open-Meteo answered a request for 11.05N/79.85E with data
for 11.0417N/79.9584E, about 12 km east. Evidence must cite the cell the server
returned, so the registry records how coarse a source is and the fetch layer
records where the value actually came from.
"""

from __future__ import annotations

import datetime as dt
from enum import StrEnum
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, Field, model_validator


class Variable(StrEnum):
    """Canonical names. Every source normalises to these, so downstream nodes
    never learn a source's local spelling."""

    WAVE_HEIGHT = "wave_height"
    WAVE_PERIOD = "wave_period"
    WAVE_DIRECTION = "wave_direction"
    WIND_SPEED = "wind_speed"
    WIND_DIRECTION = "wind_direction"
    CURRENT_SPEED = "current_speed"
    CURRENT_DIRECTION = "current_direction"
    SST = "sst"
    CHLOROPHYLL = "chlorophyll"


class SourceKind(StrEnum):
    ERDDAP = "erddap"
    COPERNICUS = "copernicus"
    OPEN_METEO = "open_meteo"
    SCRAPE = "scrape"


class AuthKind(StrEnum):
    NONE = "none"
    BASIC = "basic"
    TOKEN = "token"


class Coverage(StrEnum):
    LIVE = "live"
    STALE = "stale"
    ARCHIVE = "archive"


class VariableSpec(BaseModel):
    """One canonical variable as this source spells it."""

    native_name: str = Field(description="the variable's name in the source")
    native_unit: str = Field(description="unit as delivered, before normalisation")
    unit: str = Field(description="unit after normalisation to SI-ish canonical")
    scale: float = Field(default=1.0, description="multiply native by this")
    offset: float = Field(default=0.0, description="then add this")

    def to_canonical(self, value: float) -> float:
        return value * self.scale + self.offset


class SpatialExtent(BaseModel):
    lat_min: float = Field(ge=-90, le=90)
    lat_max: float = Field(ge=-90, le=90)
    lon_min: float = Field(ge=-180, le=360)
    lon_max: float = Field(ge=-180, le=360)
    grid_resolution_deg: float = Field(gt=0)
    lon_convention: str = Field(default="-180..180", pattern=r"^(-180\.\.180|0\.\.360)$")

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.lat_min >= self.lat_max:
            raise ValueError("lat_min must be < lat_max")
        if self.lon_min >= self.lon_max:
            raise ValueError("lon_min must be < lon_max")
        return self

    def contains(self, lat: float, lon: float) -> bool:
        if self.lon_convention == "0..360" and lon < 0:
            lon += 360
        return self.lat_min <= lat <= self.lat_max and self.lon_min <= lon <= self.lon_max


class TemporalExtent(BaseModel):
    coverage_start: dt.datetime
    coverage_end: dt.datetime | None = Field(
        default=None, description="None means rolling/live; a date means it stopped there"
    )
    cadence: str = Field(description="ISO-8601-ish duration, e.g. PT1H, P1D")
    forecast_horizon_hours: int = Field(default=0, ge=0)

    def coverage_at(self, when: dt.datetime, *, stale_after_days: int = 30) -> Coverage:
        end = self.coverage_end
        if end is None:
            return Coverage.LIVE
        if end.tzinfo is None:
            end = end.replace(tzinfo=dt.UTC)
        gap = when - end
        if gap <= dt.timedelta(days=stale_after_days):
            return Coverage.LIVE
        if gap <= dt.timedelta(days=365):
            return Coverage.STALE
        return Coverage.ARCHIVE


class DatasetEntry(BaseModel):
    id: str = Field(description="our key, unique across the registry")
    title: str
    source: SourceKind
    dataset_id: str = Field(description="the id the upstream server knows")
    endpoint: str
    auth: AuthKind = AuthKind.NONE
    variables: dict[Variable, VariableSpec]
    spatial: SpatialExtent
    temporal: TemporalExtent
    latency_hours: float = Field(default=0, ge=0, description="publish lag behind real time")
    notes: str = ""

    def is_live_at(self, when: dt.datetime) -> bool:
        return self.temporal.coverage_at(when) is Coverage.LIVE

    def serves(self, variable: Variable, lat: float, lon: float, when: dt.datetime) -> bool:
        return (
            variable in self.variables and self.spatial.contains(lat, lon) and self.is_live_at(when)
        )


class Registry(BaseModel):
    datasets: list[DatasetEntry]

    @model_validator(mode="after")
    def _unique_ids(self) -> Self:
        seen = [d.id for d in self.datasets]
        dupes = {i for i in seen if seen.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate dataset ids: {sorted(dupes)}")
        return self

    @classmethod
    def load(cls, path: Path | str = "data/registry.yaml") -> Registry:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(raw)

    def by_id(self, dataset_id: str) -> DatasetEntry:
        for d in self.datasets:
            if d.id == dataset_id:
                return d
        raise KeyError(dataset_id)

    def candidates(
        self, variable: Variable, lat: float, lon: float, when: dt.datetime
    ) -> list[DatasetEntry]:
        """Every dataset that can answer, best latency first.

        Returns a list rather than one entry so the caller can fall through when a
        source is down — a failed fetch must not become a missing number.
        """
        hits = [d for d in self.datasets if d.serves(variable, lat, lon, when)]
        return sorted(hits, key=lambda d: (d.latency_hours, d.spatial.grid_resolution_deg))
