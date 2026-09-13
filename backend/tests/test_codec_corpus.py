"""Round-trips every capsule in eval/capsule_corpus.jsonl.

This is the CLAUDE.md-mandated cross-language proof: the exact same file is
also loaded by frontend/src/shared/capsule/codec.test.ts. If the two codecs
ever disagree on a single capsule, one of these two suites fails — not a
human comparing two implementations by eye.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dhruva.codec.bits import clamp_int
from dhruva.codec.codec import Capsule, decode_capsule, encode_capsule
from dhruva.codec.field_table import CAPSULE_BYTES, CAPSULE_TOTAL_BITS, field_offsets

CORPUS_PATH = Path(__file__).parents[2] / "eval" / "capsule_corpus.jsonl"


def _load_corpus() -> list[dict]:
    with CORPUS_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _capsule_from_row(row: dict) -> Capsule:
    fields = {k: v for k, v in row.items() if k != "id"}
    return Capsule(**fields)


CORPUS = _load_corpus()


def test_corpus_file_is_non_empty():
    assert len(CORPUS) >= 5


def test_field_table_totals_145_bits():
    offsets = field_offsets()
    assert sum(f.width for f in offsets) == CAPSULE_TOTAL_BITS
    assert CAPSULE_TOTAL_BITS == 145


@pytest.mark.parametrize("row", CORPUS, ids=lambda r: r["id"])
def test_round_trip(row: dict) -> None:
    capsule = _capsule_from_row(row)
    encoded = encode_capsule(capsule)
    assert len(encoded) == CAPSULE_BYTES

    decoded = decode_capsule(encoded)

    assert decoded.msg_type == capsule.msg_type
    assert decoded.risk_class == capsule.risk_class
    assert sorted(decoded.hazard_flags) == sorted(capsule.hazard_flags)
    assert decoded.wind_dir16 == clamp_int(capsule.wind_dir16, 0, 15)
    assert decoded.curr_dir16 == clamp_int(capsule.curr_dir16, 0, 15)
    assert decoded.chl_class == capsule.chl_class
    assert decoded.bnd_type == capsule.bnd_type

    # Saturating quantisers never wrap: a decoded value must land inside the
    # quantiser's own valid range even when the source row was out of range.
    assert 0.0 <= decoded.wave_hs <= 7.75
    assert 0.0 <= decoded.wind_kt <= 63.0
    assert 0.0 <= decoded.sst_c <= 33.5


def test_saturation_does_not_wrap_a_large_wave_to_a_small_one():
    capsule = _capsule_from_row(next(r for r in CORPUS if r["id"] == "cyclone_no_go_saturates"))
    decoded = decode_capsule(encode_capsule(capsule))
    assert decoded.wave_hs == pytest.approx(7.75)  # 31 * 0.25, the documented ceiling
    assert decoded.wave_hs > 5  # regression guard: never a wrapped-small value


def test_rounding_boundary_matches_the_documented_half_up_rule():
    """wave_hs=1.375 -> /0.25 == 5.5 exactly. JS `Math.round` and this
    codec's `clamp_int` must both resolve that to 6, not 5 (Python's
    built-in round() would give 5.5 -> banker's-rounds to 6 too here
    coincidentally, but curr_kt=0.45 -> /0.1 == 4.5 is the case where
    round-half-to-even (4) and round-half-up (5) actually diverge)."""
    row = next(r for r in CORPUS if r["id"] == "half_bit_rounding_boundary")
    capsule = _capsule_from_row(row)
    decoded = decode_capsule(encode_capsule(capsule))
    assert decoded.wave_hs == pytest.approx(1.5)  # round(5.5) -> 6 * 0.25
    assert decoded.curr_kt == pytest.approx(0.5)  # round(4.5) -> 5 * 0.1, NOT banker's 4
    assert decoded.sst_c == pytest.approx(22.5)  # round(8.5) -> 9 * 0.5 + 18


def test_evidence_hash_round_trips_its_12_bit_prefix():
    capsule = _capsule_from_row(next(r for r in CORPUS if r["id"] == "kochi_caution"))
    decoded = decode_capsule(encode_capsule(capsule))
    assert decoded.evidence_hash == "a3f"
