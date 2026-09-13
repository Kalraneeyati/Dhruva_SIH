"""The 145-bit capsule codec — Python half of the pair with
frontend/src/shared/capsule/codec.ts. `tests/test_codec_corpus.py` runs the
same `eval/capsule_corpus.json` fixtures the TypeScript test suite runs,
proving the two implementations agree byte-for-byte, per CLAUDE.md: "Python
and TypeScript run the same corpus in CI."
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dhruva.codec.bits import BitReader, BitWriter, clamp_int
from dhruva.codec.enums import (
    BOUNDARY_TYPE_VALUES,
    CHL_CLASS_VALUES,
    MSG_TYPE_VALUES,
    RISK_CLASS_VALUES,
    decode_enum,
    decode_hazard_flags,
    encode_enum,
    encode_hazard_flags,
)
from dhruva.codec.field_table import CAPSULE_BYTES, CAPSULE_TOTAL_BITS, WIDTH_BY_NAME
from dhruva.codec.quantizers import (
    dequantize_bnd_dist_nm,
    dequantize_bnd_eta_min,
    dequantize_curr_kt,
    dequantize_pfz_dist_nm,
    dequantize_sst,
    dequantize_wave_hs,
    dequantize_wind_kt,
    quantize_bnd_dist_nm,
    quantize_bnd_eta_min,
    quantize_curr_kt,
    quantize_pfz_dist_nm,
    quantize_sst,
    quantize_wave_hs,
    quantize_wind_kt,
)

__all__ = ["Capsule", "encode_capsule", "decode_capsule"]


@dataclass(slots=True)
class Capsule:
    msg_type: str = "advisory"
    schema_ver: int = 1
    issue_slot: int = 0
    valid_hours: int = 6
    zone_id: int = 0
    lat_offset: int = 0
    lon_offset: int = 0
    risk_class: str = "unknown"
    hazard_flags: list[str] = field(default_factory=list)
    wave_hs: float = 0.0
    wind_kt: float = 0.0
    wind_dir16: int = 0
    curr_kt: float = 0.0
    curr_dir16: int = 0
    sst_c: float = 18.0
    chl_class: str = "low"
    pfz_bearing16: int = 0
    pfz_dist_nm: float = 0.0
    pfz_confidence: int = 0
    bnd_dist_nm: float = 0.0
    bnd_type: str = "none"
    bnd_eta_min: float = 0.0
    reason_code: int = 0
    evidence_hash: str = "000"


def _w(name: str) -> int:
    return WIDTH_BY_NAME[name]


def encode_capsule(c: Capsule) -> bytes:
    w = BitWriter(CAPSULE_BYTES * 8)
    w.write(encode_enum(MSG_TYPE_VALUES, c.msg_type), _w("msg_type"))
    w.write(clamp_int(c.schema_ver, 0, 2 ** _w("schema_ver") - 1), _w("schema_ver"))
    w.write(clamp_int(c.issue_slot, 0, 2 ** _w("issue_slot") - 1), _w("issue_slot"))
    w.write(clamp_int(c.valid_hours, 0, 2 ** _w("valid_hours") - 1), _w("valid_hours"))
    w.write(clamp_int(c.zone_id, 0, 2 ** _w("zone_id") - 1), _w("zone_id"))
    w.write(clamp_int(c.lat_offset, 0, 255), _w("lat_offset"))
    w.write(clamp_int(c.lon_offset, 0, 255), _w("lon_offset"))
    w.write(encode_enum(RISK_CLASS_VALUES, c.risk_class), _w("risk_class"))
    w.write(encode_hazard_flags(c.hazard_flags), _w("hazard_flags"))
    w.write(quantize_wave_hs(c.wave_hs), _w("wave_hs"))
    w.write(quantize_wind_kt(c.wind_kt), _w("wind_kt"))
    w.write(clamp_int(c.wind_dir16, 0, 15), _w("wind_dir"))
    w.write(quantize_curr_kt(c.curr_kt), _w("curr_kt"))
    w.write(clamp_int(c.curr_dir16, 0, 15), _w("curr_dir"))
    w.write(quantize_sst(c.sst_c), _w("sst"))
    w.write(encode_enum(CHL_CLASS_VALUES, c.chl_class), _w("chl_class"))
    w.write(clamp_int(c.pfz_bearing16, 0, 15), _w("pfz_bearing"))
    w.write(quantize_pfz_dist_nm(c.pfz_dist_nm), _w("pfz_dist_nm"))
    w.write(clamp_int(c.pfz_confidence, 0, 3), _w("pfz_conf"))
    w.write(quantize_bnd_dist_nm(c.bnd_dist_nm), _w("bnd_dist_nm"))
    w.write(encode_enum(BOUNDARY_TYPE_VALUES, c.bnd_type), _w("bnd_type"))
    w.write(quantize_bnd_eta_min(c.bnd_eta_min), _w("bnd_eta_min"))
    w.write(clamp_int(c.reason_code, 0, 255), _w("reason_code"))
    w.write(_parse_evidence_hash(c.evidence_hash), _w("evidence_hash"))
    return w.to_bytes()


def decode_capsule(data: bytes) -> Capsule:
    if len(data) < CAPSULE_BYTES:
        raise ValueError(f"capsule must be at least {CAPSULE_BYTES} bytes, got {len(data)}")
    r = BitReader(data)
    c = Capsule()
    c.msg_type = decode_enum(MSG_TYPE_VALUES, r.read(_w("msg_type")))
    c.schema_ver = r.read(_w("schema_ver"))
    c.issue_slot = r.read(_w("issue_slot"))
    c.valid_hours = r.read(_w("valid_hours"))
    c.zone_id = r.read(_w("zone_id"))
    c.lat_offset = r.read(_w("lat_offset"))
    c.lon_offset = r.read(_w("lon_offset"))
    c.risk_class = decode_enum(RISK_CLASS_VALUES, r.read(_w("risk_class")))
    c.hazard_flags = decode_hazard_flags(r.read(_w("hazard_flags")))
    c.wave_hs = dequantize_wave_hs(r.read(_w("wave_hs")))
    c.wind_kt = dequantize_wind_kt(r.read(_w("wind_kt")))
    c.wind_dir16 = r.read(_w("wind_dir"))
    c.curr_kt = dequantize_curr_kt(r.read(_w("curr_kt")))
    c.curr_dir16 = r.read(_w("curr_dir"))
    c.sst_c = dequantize_sst(r.read(_w("sst")))
    c.chl_class = decode_enum(CHL_CLASS_VALUES, r.read(_w("chl_class")))
    c.pfz_bearing16 = r.read(_w("pfz_bearing"))
    c.pfz_dist_nm = dequantize_pfz_dist_nm(r.read(_w("pfz_dist_nm")))
    c.pfz_confidence = r.read(_w("pfz_conf"))
    c.bnd_dist_nm = dequantize_bnd_dist_nm(r.read(_w("bnd_dist_nm")))
    c.bnd_type = decode_enum(BOUNDARY_TYPE_VALUES, r.read(_w("bnd_type")))
    c.bnd_eta_min = dequantize_bnd_eta_min(r.read(_w("bnd_eta_min")))
    c.reason_code = r.read(_w("reason_code"))
    c.evidence_hash = _format_evidence_hash(r.read(_w("evidence_hash")))
    return c


def _parse_evidence_hash(hash_str: str) -> int:
    prefix = (hash_str[:3] or "0").ljust(3, "0")
    return clamp_int(int(prefix, 16), 0, 4095)


def _format_evidence_hash(raw: int) -> str:
    return format(raw, "x").rjust(3, "0")


assert CAPSULE_TOTAL_BITS == 145  # documents the invariant at import time too
