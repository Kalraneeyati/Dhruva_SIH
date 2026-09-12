"""Open-Meteo adapter — the marine endpoint for waves and SST, the forecast
endpoint for wind. They are separate APIs on separate grids, so both are
registered separately and each records its own answering cell.
"""

from __future__ import annotations

import datetime as dt

import httpx

from dhruva.sources.base import FetchError, FetchOutcome, Observation
from dhruva.sources.registry import DatasetEntry, Variable

TIMEOUT = httpx.Timeout(20.0, connect=10.0)


class OpenMeteoAdapter:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

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

        native = [entry.variables[v].native_name for v in wanted]
        params: dict[str, str | float] = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(native),
            "timezone": "UTC",
            "start_date": when.date().isoformat(),
            "end_date": when.date().isoformat(),
        }
        # Ask for knots directly rather than converting; one less place to be wrong.
        if any(v is Variable.WIND_SPEED for v in wanted):
            params["wind_speed_unit"] = "kn"

        client = self._client or httpx.AsyncClient(timeout=TIMEOUT)
        try:
            r = await client.get(entry.endpoint, params=params)
            r.raise_for_status()
            payload = r.json()
        except Exception as exc:  # a dead provider is data, not a crash
            return FetchOutcome(
                errors=[FetchError(dataset_id=entry.id, error=f"{type(exc).__name__}: {exc}")]
            )
        finally:
            if self._client is None:
                await client.aclose()

        if "error" in payload:
            return FetchOutcome(
                errors=[FetchError(dataset_id=entry.id, error=str(payload.get("reason")))]
            )

        return self._parse(payload, entry, wanted, lat, lon, when)

    def _parse(
        self,
        payload: dict,
        entry: DatasetEntry,
        wanted: list[Variable],
        lat: float,
        lon: float,
        when: dt.datetime,
    ) -> FetchOutcome:
        hourly = payload.get("hourly") or {}
        times = hourly.get("time") or []
        if not times:
            return FetchOutcome(
                errors=[FetchError(dataset_id=entry.id, error="no hourly block in response")]
            )

        idx = _nearest_hour_index(times, when)
        # The cell that answered, which is not the cell requested.
        cell_lat = float(payload["latitude"])
        cell_lon = float(payload["longitude"])
        valid = dt.datetime.fromisoformat(times[idx]).replace(tzinfo=dt.UTC)
        now = dt.datetime.now(dt.UTC)

        out = FetchOutcome()
        for var in wanted:
            spec = entry.variables[var]
            series = hourly.get(spec.native_name)
            if series is None or idx >= len(series) or series[idx] is None:
                out.errors.append(
                    FetchError(
                        dataset_id=entry.id,
                        variable=var,
                        error=f"{spec.native_name} absent or null at {times[idx]}",
                    )
                )
                continue
            out.observations.append(
                Observation(
                    variable=var,
                    value=spec.to_canonical(float(series[idx])),
                    unit=spec.unit,
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
        return out


def _nearest_hour_index(times: list[str], when: dt.datetime) -> int:
    target = when.astimezone(dt.UTC).replace(tzinfo=None)
    best, best_gap = 0, None
    for i, t in enumerate(times):
        gap = abs((dt.datetime.fromisoformat(t) - target).total_seconds())
        if best_gap is None or gap < best_gap:
            best, best_gap = i, gap
    return best
