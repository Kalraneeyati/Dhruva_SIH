"""RFC 4648 base32 (no padding) — matches
frontend/src/shared/capsule/base32.ts exactly, same alphabet, so a capsule
encoded by one side decodes on the other."""

from __future__ import annotations

_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
_INDEX = {ch: i for i, ch in enumerate(_ALPHABET)}


def base32_encode(data: bytes) -> str:
    bits = 0
    value = 0
    out: list[str] = []
    for byte in data:
        value = (value << 8) | byte
        bits += 8
        while bits >= 5:
            out.append(_ALPHABET[(value >> (bits - 5)) & 31])
            bits -= 5
    if bits > 0:
        out.append(_ALPHABET[(value << (5 - bits)) & 31])
    return "".join(out)


def base32_decode(text: str) -> bytes:
    clean = [ch for ch in text.upper() if ch in _INDEX]
    bits = 0
    value = 0
    out = bytearray()
    for ch in clean:
        value = (value << 5) | _INDEX[ch]
        bits += 5
        if bits >= 8:
            out.append((value >> (bits - 8)) & 0xFF)
            bits -= 8
    return bytes(out)
