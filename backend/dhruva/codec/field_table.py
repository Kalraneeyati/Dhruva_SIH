"""The 145-bit capsule field table.

Must stay byte-for-byte identical in meaning to
frontend/src/shared/capsule/fieldTable.ts — `tests/test_codec_corpus.py` and
the frontend's `codec.test.ts` both run
`eval/capsule_corpus.json` and must agree on every capsule in it. If this
table and the TypeScript one ever diverge, that shared corpus test is what
catches it, not code review.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FieldSpec:
    name: str
    width: int


FIELD_TABLE: tuple[FieldSpec, ...] = (
    FieldSpec("msg_type", 4),
    FieldSpec("schema_ver", 3),
    FieldSpec("issue_slot", 10),
    FieldSpec("valid_hours", 4),
    FieldSpec("zone_id", 20),
    FieldSpec("lat_offset", 8),
    FieldSpec("lon_offset", 8),
    FieldSpec("risk_class", 2),
    FieldSpec("hazard_flags", 8),
    FieldSpec("wave_hs", 5),
    FieldSpec("wind_kt", 6),
    FieldSpec("wind_dir", 4),
    FieldSpec("curr_kt", 5),
    FieldSpec("curr_dir", 4),
    FieldSpec("sst", 5),
    FieldSpec("chl_class", 2),
    FieldSpec("pfz_bearing", 4),
    FieldSpec("pfz_dist_nm", 6),
    FieldSpec("pfz_conf", 2),
    FieldSpec("bnd_dist_nm", 5),
    FieldSpec("bnd_type", 2),
    FieldSpec("bnd_eta_min", 8),
    FieldSpec("reason_code", 8),
    FieldSpec("evidence_hash", 12),
)

CAPSULE_TOTAL_BITS = 145
NAVIC_SEGMENT_BITS = 220
CAPSULE_BYTES = 19  # ceil(145/8)


@dataclass(frozen=True, slots=True)
class FieldOffset(FieldSpec):
    offset: int


def field_offsets() -> list[FieldOffset]:
    offset = 0
    out: list[FieldOffset] = []
    for f in FIELD_TABLE:
        out.append(FieldOffset(f.name, f.width, offset))
        offset += f.width
    return out


def _assert_table_integrity() -> None:
    offsets = field_offsets()
    total = sum(f.width for f in offsets)
    if total != CAPSULE_TOTAL_BITS:
        raise AssertionError(f"capsule field table is {total} bits, expected exactly {CAPSULE_TOTAL_BITS}")
    seen: set[str] = set()
    for f in offsets:
        if f.name in seen:
            raise AssertionError(f"duplicate capsule field: {f.name}")
        seen.add(f.name)
    prev_end = 0
    for f in offsets:
        if f.offset != prev_end:
            raise AssertionError(f"capsule field {f.name} does not start where the prior field ends")
        prev_end = f.offset + f.width


_assert_table_integrity()

WIDTH_BY_NAME: dict[str, int] = {f.name: f.width for f in field_offsets()}
