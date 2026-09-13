"""MSB-first bit packing over a byte array — the Python half of the pair with
frontend/src/shared/capsule/bits.ts. Pure: no network, no filesystem, no
clock, per CLAUDE.md's requirement that the decoder run forever offline.
"""

from __future__ import annotations

import math


class BitWriter:
    def __init__(self, total_bits: int) -> None:
        self._bytes = bytearray((total_bits + 7) // 8)
        self._bit_pos = 0

    def write(self, value: int, width: int) -> None:
        if value < 0 or value >= (1 << width):
            raise ValueError(f"value {value} does not fit in {width} bits")
        for i in range(width - 1, -1, -1):
            bit = (value >> i) & 1
            byte_index = self._bit_pos >> 3
            bit_in_byte = 7 - (self._bit_pos & 7)
            if bit:
                self._bytes[byte_index] |= 1 << bit_in_byte
            self._bit_pos += 1

    def to_bytes(self) -> bytes:
        return bytes(self._bytes)


class BitReader:
    def __init__(self, data: bytes) -> None:
        self._bytes = data
        self._bit_pos = 0

    def read(self, width: int) -> int:
        value = 0
        for _ in range(width):
            byte_index = self._bit_pos >> 3
            bit_in_byte = 7 - (self._bit_pos & 7)
            bit = (self._bytes[byte_index] >> bit_in_byte) & 1
            value = (value << 1) | bit
            self._bit_pos += 1
        return value


def _round_half_up(value: float) -> int:
    """Matches JS `Math.round` exactly (== `floor(x + 0.5)`), which is NOT
    what Python's built-in `round()` does — Python rounds half-to-even
    (round(4.5) == 4), JS rounds half-up (Math.round(4.5) == 5). Left
    unreconciled, the two codecs would silently diverge on any input that
    lands exactly on a .5 quantisation boundary, which the shared corpus test
    (tests/test_codec_corpus.py) exists specifically to catch."""
    return math.floor(value + 0.5)


def clamp_int(value: float, lo: int, hi: int) -> int:
    """Clamp, never wrap. CLAUDE.md: "Wrapping a 9m sea into a calm reading is
    the worst bug we can ship." Rounds to nearest int before clamping, same as
    the TypeScript twin."""
    return max(lo, min(hi, _round_half_up(value)))
