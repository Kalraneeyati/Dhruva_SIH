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

from dhruva.sources.base import (
    FetchError,
    FetchOutcome,
    Observation,
    unusable_reason,
    uv_to_speed_direction,
)
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

        # Collapse time and depth but keep the lat/lon grid, so a land cell can
        # fall back to the nearest cell that actually has water in it.
        try:
            field = ds
            if "time" in field.dims or "time" in field.coords:
                field = field.sel(time=_naive(when), method="nearest")
            if "depth" in field.dims:
                field = field.isel(depth=0)
        except Exception as exc:
            return FetchOutcome(
                errors=[FetchError(dataset_id=entry.id, error=f"select failed: {exc}")]
            )

        valid = _valid_time(field, when)
        cell_lat, cell_lon = lat, lon

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
            picked = _nearest_wet(field, "uo", lat, lon)
            if picked is None:
                out.errors.append(
                    FetchError(dataset_id=entry.id, error="no wet cell for uo within the tile")
                )
            else:
                u, cell_lat, cell_lon = picked
                # Read the partner component at the *same* cell; mixing cells would
                # combine two different places into one vector.
                v = float(field["vo"].sel(latitude=cell_lat, longitude=cell_lon).values)
                reason = unusable_reason(v)
                if reason:
                    out.errors.append(FetchError(dataset_id=entry.id, error=f"vo: {reason}"))
                else:
                    speed_ms, bearing = uv_to_speed_direction(u, v)
                    if Variable.CURRENT_SPEED in wanted:
                        emit(Variable.CURRENT_SPEED, speed_ms * MS_TO_KT, "kt")
                    if Variable.CURRENT_DIRECTION in wanted:
                        emit(Variable.CURRENT_DIRECTION, bearing, "degree")

        for var in wanted:
            if var in DERIVED_FROM_UV:
                continue
            spec = entry.variables[var]
            picked = _nearest_wet(field, spec.native_name, lat, lon)
            if picked is None:
                out.errors.append(
                    FetchError(
                        dataset_id=entry.id,
                        variable=var,
                        error=f"{spec.native_name}: no wet cell within the tile",
                    )
                )
                continue
            raw, cell_lat, cell_lon = picked
            emit(var, spec.to_canonical(raw), spec.unit)

        return out


def _nearest_wet(
    field: xr.Dataset, name: str, lat: float, lon: float
) -> tuple[float, float, float] | None:
    """Nearest grid cell holding real data, with the cell it came from.

    The plain nearest cell to a coastal point is often land, where ocean models
    store NaN — at 11.05N/79.85E the 0.25 degree biogeochemistry grid lands on
    shore. Searching outward for the nearest wet cell keeps the answer honest,
    because the cell returned is reported and offset_km shows how far it is.
    """
    import numpy as np

    if name not in field:
        return None
    values = np.asarray(field[name].values, dtype="float64")
    lats = np.asarray(field["latitude"].values, dtype="float64")
    lons = np.asarray(field["longitude"].values, dtype="float64")
    if values.shape != (lats.size, lons.size):
        values = np.squeeze(values)
        if values.shape != (lats.size, lons.size):
            return None

    finite = np.isfinite(values)
    if not finite.any():
        return None

    grid_lat, grid_lon = np.meshgrid(lats, lons, indexing="ij")
    scale = np.cos(np.radians(lat))
    dist = ((grid_lat - lat) * 111.32) ** 2 + ((grid_lon - lon) * 111.32 * scale) ** 2
    dist = np.where(finite, dist, np.inf)
    i, j = np.unravel_index(int(np.argmin(dist)), dist.shape)
    return float(values[i, j]), float(lats[i]), float(lons[j])


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
