"""Enum wire-value orderings for the capsule codec — mirrors
frontend/src/shared/capsule/enums.ts. The array index IS the raw wire value;
never reorder these once a capsule has shipped.
"""

from __future__ import annotations

MSG_TYPE_VALUES = ("advisory", "alert", "all_clear", "test")
RISK_CLASS_VALUES = ("safe", "caution", "no_go", "unknown")
CHL_CLASS_VALUES = ("low", "moderate", "high", "very_high")
BOUNDARY_TYPE_VALUES = ("none", "imbl", "mpa", "closed")

# Offset 59, width 8 (CLAUDE.md) — bit order fixed, MSB..LSB in this list order.
HAZARD_BIT_ORDER = ("wave", "wind", "squall", "lightning", "cyclone", "current", "fog", "tsunami")


def encode_enum(values: tuple[str, ...], value: str) -> int:
    try:
        return values.index(value)
    except ValueError as exc:
        raise ValueError(f"unknown enum value {value!r}") from exc


def decode_enum(values: tuple[str, ...], raw: int) -> str:
    if raw < 0 or raw >= len(values):
        raise ValueError(f"enum raw value {raw} out of range for {values!r}")
    return values[raw]


def encode_hazard_flags(flags: list[str]) -> int:
    raw = 0
    n = len(HAZARD_BIT_ORDER)
    for f in flags:
        idx = HAZARD_BIT_ORDER.index(f)
        raw |= 1 << (n - 1 - idx)
    return raw


def decode_hazard_flags(raw: int) -> list[str]:
    n = len(HAZARD_BIT_ORDER)
    return [f for i, f in enumerate(HAZARD_BIT_ORDER) if raw & (1 << (n - 1 - i))]
