"""The numeric firewall — IMPLEMENTATION.md 3.3.

"The model may not introduce a number." This module is the enforcement:
`extract_numbers` pulls every numeric token out of a piece of narration —
ASCII digits, Devanagari digits, and Tamil digits, per CLAUDE.md — and
`validate_narration` checks each one against the evidence bundle that
produced it, within a rounding tolerance, or against an explicitly declared
unit conversion. `render_template` is the safe fallback path: a template
string with `{slot}` placeholders filled only from the bundle can never
contain a number the bundle didn't already carry, which is what
DHRUVA actually ships today (no LLM key is configured yet — see
graph/orchestrator.py) and remains the fallback once one is.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from dhruva.evidence.schema import EvidenceBundleEntry

_ASCII_DIGITS = "0123456789"
_DEVANAGARI_DIGITS = "०१२३४५६७८९"
_TAMIL_DIGITS = "௦௧௨௩௪௫௬௭௮௯"

_DIGIT_TRANSLATION = str.maketrans(
    _DEVANAGARI_DIGITS + _TAMIL_DIGITS,
    _ASCII_DIGITS + _ASCII_DIGITS,
)

# Matches a run of digits (any of the three scripts, not mixed within one
# token) with an optional decimal point — e.g. "1.5", "१२", "௨௩.௫".
_NUMBER_PATTERN = re.compile(
    r"[0-9०-९௦-௯]+(?:\.[0-9०-९௦-௯]+)?"
)

# Unit conversions the firewall permits without the exact source value
# appearing verbatim — CLAUDE.md: "the explicitly allowed derived set (unit
# conversions declared per field, e.g. m->ft, kt->km/h)". Declared once, here,
# rather than left implicit in whichever narration happens to use them.
UNIT_CONVERSIONS: dict[str, float] = {
    "m->ft": 3.28084,
    "kt->kmh": 1.852,
    "km->nm": 0.539957,
    "nm->km": 1.852,
}

DEFAULT_TOLERANCE = 0.06  # relative tolerance for rounding in narration text


def extract_numbers(text: str) -> list[float]:
    """Every numeric token in `text`, ASCII and Indic digits alike."""
    numbers: list[float] = []
    for match in _NUMBER_PATTERN.finditer(text):
        token = match.group(0).translate(_DIGIT_TRANSLATION)
        try:
            numbers.append(float(token))
        except ValueError:
            continue
    return numbers


@dataclass(frozen=True, slots=True)
class FirewallResult:
    ok: bool
    checked: list[float]
    violations: list[float]


def _allowed_values(bundle: list[EvidenceBundleEntry]) -> set[float]:
    allowed: set[float] = set()
    for entry in bundle:
        allowed.add(entry.value)
        if entry.threshold is not None:
            allowed.add(entry.threshold)
        for factor in UNIT_CONVERSIONS.values():
            allowed.add(entry.value * factor)
    return allowed


def _matches_any(value: float, allowed: set[float], tolerance: float) -> bool:
    for candidate in allowed:
        denom = max(abs(candidate), 1e-9)
        if abs(value - candidate) / denom <= tolerance:
            return True
        if abs(value - candidate) <= tolerance:  # absolute fallback for small values
            return True
    return False


def validate_narration(
    narration: str, bundle: list[EvidenceBundleEntry], *, tolerance: float = DEFAULT_TOLERANCE
) -> FirewallResult:
    """Does every number in `narration` trace back to the evidence bundle?

    Small integers (0-9) that are far more likely to be prose ("one of two
    sources", "8 official queries") than measurements are exempted from
    failing the check on their own — CLAUDE.md's adversarial test cases target
    fabricated *measurements*, not narration mentioning a small count.
    """
    allowed = _allowed_values(bundle)
    checked = extract_numbers(narration)
    violations = [
        n for n in checked if not (n < 10 and n == int(n)) and not _matches_any(n, allowed, tolerance)
    ]
    return FirewallResult(ok=not violations, checked=checked, violations=violations)


def render_template(template: str, values: dict[str, str]) -> str:
    """Fill `{slot}` placeholders from `values` only. Cannot introduce a
    number that isn't already a formatted string in `values`."""

    def _sub(match: re.Match[str]) -> str:
        key = match.group(1)
        return values.get(key, match.group(0))

    return re.sub(r"\{(\w+)\}", _sub, template)
