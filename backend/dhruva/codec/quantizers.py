"""Physical-unit <-> raw-field conversions — mirrors
frontend/src/shared/capsule/quantizers.ts. Every quantiser clamps
(codec/bits.py::clamp_int) rather than wraps.
"""

from __future__ import annotations

import math

from dhruva.codec.bits import clamp_int

COMPASS_16_LABELS = (
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
)


def to_compass_16(bearing_deg: float) -> int:
    """Matches backend/dhruva/sources/base.py::to_compass_16 and the
    TypeScript twin exactly — demo values must sit on the same 16-point grid."""
    return int(((bearing_deg % 360.0) + 360.0) % 360.0 / 22.5 + 0.5) % 16


# bbox 6-24 deg N, 66-94 deg E, 0.05deg step (CLAUDE.md capsule spec).
ZONE_LAT_MIN = 6.0
ZONE_LAT_MAX = 24.0
ZONE_LON_MIN = 66.0
ZONE_LON_MAX = 94.0
ZONE_STEP_DEG = 0.05
ZONE_LON_CELLS = round((ZONE_LON_MAX - ZONE_LON_MIN) / ZONE_STEP_DEG)  # 560
ZONE_LAT_CELLS = round((ZONE_LAT_MAX - ZONE_LAT_MIN) / ZONE_STEP_DEG)  # 360


def encode_zone(lat: float, lon: float) -> tuple[int, int, int]:
    """Position -> (zone_id, lat_offset_raw, lon_offset_raw). Floors to find
    the cell index (never rounds — rounding an index shifts the cell and
    silently corrupts the sub-cell offset, a bug the TS test corpus caught
    during Phase 5 development)."""
    lat_idx = min(max(math.floor((lat - ZONE_LAT_MIN) / ZONE_STEP_DEG), 0), ZONE_LAT_CELLS - 1)
    lon_idx = min(max(math.floor((lon - ZONE_LON_MIN) / ZONE_STEP_DEG), 0), ZONE_LON_CELLS - 1)
    cell_lat = ZONE_LAT_MIN + lat_idx * ZONE_STEP_DEG
    cell_lon = ZONE_LON_MIN + lon_idx * ZONE_STEP_DEG
    lat_frac = clamp_int(((lat - cell_lat) / ZONE_STEP_DEG) * 256, 0, 255)
    lon_frac = clamp_int(((lon - cell_lon) / ZONE_STEP_DEG) * 256, 0, 255)
    zone_id = lat_idx * ZONE_LON_CELLS + lon_idx
    return zone_id, lat_frac, lon_frac


def decode_zone(zone_id: int, lat_offset_raw: int, lon_offset_raw: int) -> tuple[float, float]:
    lat_idx = zone_id // ZONE_LON_CELLS
    lon_idx = zone_id % ZONE_LON_CELLS
    lat = ZONE_LAT_MIN + lat_idx * ZONE_STEP_DEG + (lat_offset_raw / 256) * ZONE_STEP_DEG
    lon = ZONE_LON_MIN + lon_idx * ZONE_STEP_DEG + (lon_offset_raw / 256) * ZONE_STEP_DEG
    return lat, lon


SLOTS_PER_WEEK = 7 * 24 * 4  # 672, 15-minute slots


def encode_issue_slot(when_utc_day: int, hour: int, minute: int) -> int:
    day_of_week = ((when_utc_day % 7) + 7) % 7
    minute_of_day = hour * 60 + minute
    slot = day_of_week * (24 * 4) + minute_of_day // 15
    return clamp_int(slot, 0, SLOTS_PER_WEEK - 1)


# ---------------------------------------------------------- scalar fields ----
def quantize_wave_hs(m: float) -> int:
    return clamp_int(m / 0.25, 0, 31)


def dequantize_wave_hs(raw: int) -> float:
    return raw * 0.25


def quantize_wind_kt(kt: float) -> int:
    return clamp_int(kt, 0, 63)


def dequantize_wind_kt(raw: int) -> float:
    return float(raw)


def quantize_curr_kt(kt: float) -> int:
    return clamp_int(kt / 0.1, 0, 31)


def dequantize_curr_kt(raw: int) -> float:
    return raw * 0.1


def quantize_sst(c: float) -> int:
    return clamp_int((c - 18.0) / 0.5, 0, 31)


def dequantize_sst(raw: int) -> float:
    return raw * 0.5 + 18.0


def quantize_pfz_dist_nm(nm: float) -> int:
    return clamp_int(nm, 0, 63)


def dequantize_pfz_dist_nm(raw: int) -> float:
    return float(raw)


def quantize_bnd_dist_nm(nm: float) -> int:
    return clamp_int(nm, 0, 31)


def dequantize_bnd_dist_nm(raw: int) -> float:
    return float(raw)


def quantize_bnd_eta_min(minutes: float) -> int:
    return clamp_int(minutes, 0, 255)


def dequantize_bnd_eta_min(raw: int) -> float:
    return float(raw)
