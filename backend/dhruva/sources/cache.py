"""Zarr subset cache.

Gate 2 wants `conditions_at()` under 3 s warm. Copernicus serves ARCO stores over
the network and a cold subset takes tens of seconds, so this cache is what makes
the target reachable rather than an optimisation on top of one.

Keying is by *tile*, not by request. A request for a single point is widened to
the enclosing whole-degree tile before it becomes a key, so every boat in the
same patch of sea shares one cache entry and pre-warming a bounding box actually
pays off. Keying on the raw request bbox would give a near-zero hit rate, since
no two boats ask about the same coordinates twice.

Freshness is an attribute on the stored dataset, not a filesystem mtime: a store
can be rewritten without its contents changing, and mtime would lie about how old
the *data* is.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import math
import shutil
from dataclasses import dataclass
from pathlib import Path

import xarray as xr

FETCHED_AT_ATTR = "dhruva_fetched_at"
DATASET_ATTR = "dhruva_dataset_id"

# The demo window: the Indian EEZ box the plan is written against.
DEMO_BBOX = (6.0, 24.0, 66.0, 94.0)


@dataclass(frozen=True, slots=True)
class CacheKey:
    """Normalised identity of a cached subset."""

    dataset_id: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    time_start: dt.datetime
    time_end: dt.datetime
    variables: tuple[str, ...]

    @classmethod
    def for_point(
        cls,
        dataset_id: str,
        lat: float,
        lon: float,
        when: dt.datetime,
        variables: list[str] | tuple[str, ...],
        *,
        tile_deg: float = 1.0,
        window_hours: int = 24,
    ) -> CacheKey:
        """Widen a point request to its enclosing tile and time window."""
        return cls(
            dataset_id=dataset_id,
            lat_min=math.floor(lat / tile_deg) * tile_deg,
            lat_max=math.floor(lat / tile_deg) * tile_deg + tile_deg,
            lon_min=math.floor(lon / tile_deg) * tile_deg,
            lon_max=math.floor(lon / tile_deg) * tile_deg + tile_deg,
            time_start=_floor_hours(when, window_hours),
            time_end=_floor_hours(when, window_hours) + dt.timedelta(hours=window_hours),
            variables=tuple(sorted(variables)),
        )

    @classmethod
    def for_bbox(
        cls,
        dataset_id: str,
        bbox: tuple[float, float, float, float],
        when: dt.datetime,
        variables: list[str] | tuple[str, ...],
        *,
        window_hours: int = 24,
    ) -> CacheKey:
        lat_min, lat_max, lon_min, lon_max = bbox
        return cls(
            dataset_id=dataset_id,
            lat_min=lat_min,
            lat_max=lat_max,
            lon_min=lon_min,
            lon_max=lon_max,
            time_start=_floor_hours(when, window_hours),
            time_end=_floor_hours(when, window_hours) + dt.timedelta(hours=window_hours),
            variables=tuple(sorted(variables)),
        )

    @property
    def digest(self) -> str:
        raw = (
            f"{self.dataset_id}|{self.lat_min:.4f},{self.lat_max:.4f}"
            f"|{self.lon_min:.4f},{self.lon_max:.4f}"
            f"|{self.time_start.isoformat()},{self.time_end.isoformat()}"
            f"|{','.join(self.variables)}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()[:20]

    def covers(self, lat: float, lon: float) -> bool:
        return self.lat_min <= lat <= self.lat_max and self.lon_min <= lon <= self.lon_max


def _floor_hours(when: dt.datetime, hours: int) -> dt.datetime:
    when = when.astimezone(dt.UTC)
    seconds = hours * 3600
    epoch = int(when.timestamp()) // seconds * seconds
    return dt.datetime.fromtimestamp(epoch, dt.UTC)


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    stale: int = 0
    writes: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses + self.stale
        return self.hits / total if total else 0.0


class ZarrCache:
    """On-disk subset cache. Cold queries still work, just slower."""

    def __init__(self, root: Path | str = ".zarr_cache", default_ttl_hours: float = 6.0) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.default_ttl_hours = default_ttl_hours
        self.stats = CacheStats()

    def path_for(self, key: CacheKey) -> Path:
        return self.root / f"{key.dataset_id}__{key.digest}.zarr"

    def get(self, key: CacheKey, *, ttl_hours: float | None = None) -> xr.Dataset | None:
        """Return the cached subset, or None on miss or staleness."""
        path = self.path_for(key)
        if not path.exists():
            self.stats.misses += 1
            return None
        try:
            ds = xr.open_zarr(path, consolidated=True)
        except Exception:
            # A half-written store is a miss, not a crash. Drop it.
            shutil.rmtree(path, ignore_errors=True)
            self.stats.misses += 1
            return None

        age = self.age_of(ds)
        ttl = self.default_ttl_hours if ttl_hours is None else ttl_hours
        if age is None or age > dt.timedelta(hours=ttl):
            ds.close()
            self.stats.stale += 1
            return None

        self.stats.hits += 1
        return ds

    def put(self, key: CacheKey, ds: xr.Dataset) -> Path:
        path = self.path_for(key)
        stamped = ds.copy()
        # A dataset opened from a zarr v2 source carries that store's codecs in
        # .encoding — Copernicus hands back numcodecs Blosc — and writing those
        # into a v3 store raises "Expected a BytesBytesCodec". Drop the inherited
        # encoding and let zarr choose its own.
        for name in list(stamped.variables):
            stamped[name].encoding.clear()
        stamped.attrs[FETCHED_AT_ATTR] = dt.datetime.now(dt.UTC).isoformat()
        stamped.attrs[DATASET_ATTR] = key.dataset_id
        tmp = path.with_suffix(".zarr.tmp")
        shutil.rmtree(tmp, ignore_errors=True)
        stamped.to_zarr(tmp, mode="w", consolidated=True)
        shutil.rmtree(path, ignore_errors=True)
        tmp.rename(path)
        self.stats.writes += 1
        return path

    @staticmethod
    def age_of(ds: xr.Dataset) -> dt.timedelta | None:
        raw = ds.attrs.get(FETCHED_AT_ATTR)
        if not raw:
            return None
        try:
            stamped = dt.datetime.fromisoformat(str(raw))
        except ValueError:
            return None
        if stamped.tzinfo is None:
            stamped = stamped.replace(tzinfo=dt.UTC)
        return dt.datetime.now(dt.UTC) - stamped

    def entries(self) -> list[Path]:
        return sorted(self.root.glob("*.zarr"))

    def size_bytes(self) -> int:
        return sum(f.stat().st_size for f in self.root.rglob("*") if f.is_file())

    def prune(self, *, older_than_hours: float | None = None) -> int:
        """Drop stale stores. Returns how many went."""
        ttl = self.default_ttl_hours if older_than_hours is None else older_than_hours
        dropped = 0
        for path in self.entries():
            try:
                ds = xr.open_zarr(path, consolidated=True)
            except Exception:
                shutil.rmtree(path, ignore_errors=True)
                dropped += 1
                continue
            age = self.age_of(ds)
            ds.close()
            if age is None or age > dt.timedelta(hours=ttl):
                shutil.rmtree(path, ignore_errors=True)
                dropped += 1
        return dropped

    def clear(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)
        self.root.mkdir(parents=True, exist_ok=True)
