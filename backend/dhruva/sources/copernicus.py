"""Copernicus Marine adapter.

`copernicusmarine.open_dataset` is synchronous and talks to ARCO stores over the
network, so a cold subset costs tens of seconds. Every fetch goes through the
Zarr tile cache and the blocking call runs in a worker thread, which is what puts
Gate 2's 3 s warm target within reach.

Current speed and direction are derived here rather than registered as native
variables, because the source publishes vector components (uo, vo) and nothing
else. The registry records `native_name: "uo,vo"` for both to say so out loud.
"""

from __future__ import annotations

import asyncio
import datetime as dt
from typing import TYPE_CHECKING

from dhruva.sources.base import FetchError, FetchOutcome, Observation, uv_to_speed_direction
from dhruva.sources.cache import CacheKey, ZarrCache
from dhruva.sources.registry import DatasetEntry, Variable

if TYPE_CHECKING:
    import xarray as xr

DERIVED_FROM_UV = {Variable.CURRENT_SPEED, Variable.CURRENT_DIRECTION}
MS_TO_KT = 1.943844


class CopernicusAdapter:
    def __init__(
        self,
        cache: ZarrCache | None = None,
        *,
        username: str | None = None,
        password: str | None = None,
        tile_deg: float = 1.0,
        window_hours: int = 24,
    ) -> None:
        self.cache = cache or ZarrCache()
        self.username = username
        self.password = password
        self.tile_deg = tile_deg
        self.window_hours = window_hours

    async def fetch(
        self,
        entry: DatasetEntry,
        variables: list[Variable],
        lat: float,
        lon: float,
        when: dt.datetime,
    ) -> FetchOutcome:
        wanted = [v for v in variables if v in entry.variables]
        if not wanted:
            return FetchOutcome()

        native = self._native_names(entry, wanted)
        key = CacheKey.for_point(
            entry.id,
            lat,
            lon,
            when,
            native,
            tile_deg=self.tile_deg,
            window_hours=self.window_hours,
        )

        ds = self.cache.get(key)
        if ds is None:
            try:
                ds = await asyncio.to_thread(self._subset, entry, native, key)
            except Exception as exc:
                return FetchOutcome(
                    errors=[FetchError(dataset_id=entry.id, error=f"{type(exc).__name__}: {exc}")]
                )
            self.cache.put(key, ds)

        try:
            return self._read_point(ds, entry, wanted, lat, lon, when)
        finally:
            ds.close()

    @staticmethod
    def _native_names(entry: DatasetEntry, wanted: list[Variable]) -> list[str]:
        """Flatten "uo,vo" into its components and de-duplicate."""
        names: list[str] = []
        for v in wanted:
            for part in entry.variables[v].native_name.split(","):
                part = part.strip()
                if part and part not in names:
                    names.append(part)
        return sorted(names)

    def _subset(self, entry: DatasetEntry, native: list[str], key: CacheKey) -> xr.Dataset:
        """Blocking. Runs in a worker thread."""
        import copernicusmarine as cm

        kwargs: dict[str, object] = dict(
            dataset_id=entry.dataset_id,
            variables=native,
            minimum_latitude=key.lat_min,
            maximum_latitude=key.lat_max,
            minimum_longitude=key.lon_min,
            maximum_longitude=key.lon_max,
            start_datetime=key.time_start,
            end_datetime=key.time_end,
        )
        if self.username:
            kwargs["username"] = self.username
            kwargs["password"] = self.password
        # Surface fields only; the shallowest level is the SST and surface-current proxy.
        if entry.id == "copernicus_phy_hourly":
            kwargs["minimum_depth"] = 0.0
            kwargs["maximum_depth"] = 1.0

        ds = cm.open_dataset(**kwargs)  # type: ignore[arg-type]
        return ds.load()  # materialise inside the thread, not on the event loop

    def _read_point(
        self,
        ds: xr.Dataset,
        entry: DatasetEntry,
        wanted: list[Variable],
        lat: float,
        lon: float,
        when: dt.datetime,
    ) -> FetchOutcome:
        out = FetchOutcome()
        now = dt.datetime.now(dt.UTC)

        try:
            point = ds.sel(latitude=lat, longitude=lon, method="nearest")
            if "time" in point.dims or "time" in point.coords:
                point = point.sel(time=_naive(when), method="nearest")
            if "depth" in point.dims:
                point = point.isel(depth=0)
        except Exception as exc:
            return FetchOutcome(
                errors=[FetchError(dataset_id=entry.id, error=f"select failed: {exc}")]
            )

        cell_lat = float(point["latitude"].values)
        cell_lon = float(point["longitude"].values)
        valid = _valid_time(point, when)

        def emit(var: Variable, value: float, unit: str) -> None:
            out.observations.append(
                Observation(
                    variable=var,
                    value=value,
                    unit=unit,
                    dataset_id=entry.id,
                    upstream_dataset_id=entry.dataset_id,
                    valid_time=valid,
                    cell_lat=cell_lat,
                    cell_lon=cell_lon,
                    requested_lat=lat,
                    requested_lon=lon,
                    grid_resolution_deg=entry.spatial.grid_resolution_deg,
                    is_forecast=valid > now,
                    fetched_at=now,
                )
            )

        if DERIVED_FROM_UV & set(wanted):
            try:
                u = float(point["uo"].values)
                v = float(point["vo"].values)
                speed_ms, bearing = uv_to_speed_direction(u, v)
                if Variable.CURRENT_SPEED in wanted:
                    emit(Variable.CURRENT_SPEED, speed_ms * MS_TO_KT, "kt")
                if Variable.CURRENT_DIRECTION in wanted:
                    emit(Variable.CURRENT_DIRECTION, bearing, "degree")
            except (KeyError, ValueError) as exc:
                out.errors.append(
                    FetchError(dataset_id=entry.id, error=f"uo/vo unavailable: {exc}")
                )

        for var in wanted:
            if var in DERIVED_FROM_UV:
                continue
            spec = entry.variables[var]
            try:
                raw = float(point[spec.native_name].values)
            except (KeyError, ValueError) as exc:
                out.errors.append(
                    FetchError(
                        dataset_id=entry.id, variable=var, error=f"{spec.native_name}: {exc}"
                    )
                )
                continue
            emit(var, spec.to_canonical(raw), spec.unit)

        return out


def _naive(when: dt.datetime) -> dt.datetime:
    """Copernicus time coordinates are tz-naive UTC; comparing them against an
    aware datetime raises."""
    return when.astimezone(dt.UTC).replace(tzinfo=None)


def _valid_time(point: xr.Dataset, fallback: dt.datetime) -> dt.datetime:
    if "time" not in point.coords:
        return fallback
    import numpy as np

    # Via an ISO string: the coordinate is a 0-d datetime64 array and feeding that
    # straight to a datetime constructor is neither type-safe nor unit-stable.
    iso = str(np.datetime_as_string(point["time"].values, unit="s"))
    return dt.datetime.fromisoformat(iso).replace(tzinfo=dt.UTC)
