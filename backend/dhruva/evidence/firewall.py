"""The numeric firewall.

The rule: the model may not introduce a number. Every numeric token in narration
must trace to a value in the evidence bundle, or to a declared conversion of one.
A hallucinated wave height becomes structurally impossible rather than merely
unlikely, and that is the whole trust story.

Extraction is the part that quietly fails. Three ways a number gets past a naive
validator:

ASCII digits are not the only digits. Tamil (௦-௯), Devanagari (०-९), Bengali,
Telugu, Gujarati, Odia and Kannada all have their own, and the narration is
produced in twelve languages. Python's \\d matches them, but int() and float()
do not accept them mixed with an ASCII decimal point, so they are transliterated
before parsing rather than assumed to work.

Numbers get spelled out. "two point four metres", "இரண்டு", "दो" — a digit-only
regex sees nothing at all, which is the most dangerous miss because the sentence
still reads like a measurement.

Units get converted. 2.4 m is also 7.9 ft and that is not a fabrication, so
declared conversions are allowed and anything else is not.

On failure the caller retries once with a stricter prompt, and on a second
failure renders the pure template. The unvalidated string is never shipped.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from dhruva.evidence.schema import EvidenceBundle

# Absolute slack for float noise only. Narration rounding is handled by matching
# against rounded candidates, not by widening a band around them — see
# _matches_any for why a relative band is a hole rather than a tolerance.
DEFAULT_TOLERANCE = 1e-6

# Conversions a narration may perform without the result counting as invented.
# Anything not listed here is a fabrication, including plausible ones.
DECLARED_CONVERSIONS: dict[str, list[tuple[str, float, float]]] = {
    "m": [("ft", 3.280839895, 0.0)],
    "kt": [("km/h", 1.852, 0.0), ("m/s", 0.5144444, 0.0)],
    "nm": [("km", 1.852, 0.0)],
    "km": [("nm", 0.539957, 0.0)],
    "degC": [("degF", 1.8, 32.0)],
}

# Spelled-out numerals. Only small integers: narration that spells out a decimal
# is rare, and a short list that is certainly correct beats a long list that is
# not. Anything unrecognised stays unrecognised and is reported, not waved past.
_WORD_NUMBERS: dict[str, dict[str, float]] = {
    "en": {
        "zero": 0,
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "twenty": 20,
        "thirty": 30,
        "forty": 40,
        "fifty": 50,
        "sixty": 60,
        "hundred": 100,
    },
    "ta": {
        "பூஜ்ஜியம்": 0,
        "ஒன்று": 1,
        "இரண்டு": 2,
        "மூன்று": 3,
        "நான்கு": 4,
        "ஐந்து": 5,
        "ஆறு": 6,
        "ஏழு": 7,
        "எட்டு": 8,
        "ஒன்பது": 9,
        "பத்து": 10,
        "நூறு": 100,
    },
    "hi": {
        "शून्य": 0,
        "एक": 1,
        "दो": 2,
        "तीन": 3,
        "चार": 4,
        "पांच": 5,
        "पाँच": 5,
        "छह": 6,
        "सात": 7,
        "आठ": 8,
        "नौ": 9,
        "दस": 10,
        "सौ": 100,
    },
}

_NUMBER_TOKEN = re.compile(r"\d[\d,]*(?:[.٫]\d+)?", re.UNICODE)


@dataclass(frozen=True, slots=True)
class Violation:
    token: str
    value: float
    reason: str


@dataclass
class FirewallResult:
    passed: bool
    violations: list[Violation] = field(default_factory=list)
    checked: list[float] = field(default_factory=list)
    unparsed: list[str] = field(default_factory=list)

    @property
    def messages(self) -> list[str]:
        return [f"{v.token!r} ({v.value:g}): {v.reason}" for v in self.violations]


def transliterate_digits(text: str) -> str:
    """Map any Unicode decimal digit to ASCII.

    unicodedata.digit() knows every script's digits, so this does not need a
    per-language table and does not go stale when a language is added.
    """
    out: list[str] = []
    for ch in text:
        if ch.isdigit() and not ch.isascii():
            try:
                out.append(str(unicodedata.digit(ch)))
                continue
            except (TypeError, ValueError):
                pass
        out.append(ch)
    return "".join(out)


def extract_numbers(text: str, language: str = "en") -> tuple[list[tuple[str, float]], list[str]]:
    """Every number in the narration, as (token, value), plus unparsed tokens."""
    normalised = transliterate_digits(text)
    found: list[tuple[str, float]] = []
    unparsed: list[str] = []

    for match in _NUMBER_TOKEN.finditer(normalised):
        if _is_unit_exponent(normalised, match.start()):
            continue
        raw = match.group(0)
        cleaned = raw.replace(",", "").replace("٫", ".")
        try:
            found.append((raw, float(cleaned)))
        except ValueError:
            unparsed.append(raw)

    words = _WORD_NUMBERS.get(language, {}) | _WORD_NUMBERS["en"]
    if words:
        pattern = re.compile(
            "|".join(sorted((re.escape(w) for w in words), key=len, reverse=True)),
            re.IGNORECASE | re.UNICODE,
        )
        for match in pattern.finditer(text):
            if not _is_standalone(text, match.start(), match.end()):
                continue
            token = match.group(0)
            value = words.get(token) or words.get(token.lower())
            if value is not None:
                found.append((token, float(value)))

    return found, unparsed


def _is_unit_exponent(text: str, start: int) -> bool:
    """Is this digit part of a unit rather than a measurement?

    Chlorophyll is quoted in "mg m-3" and the 3 there is an exponent, not a
    reading. Without this every narration that names the unit reports a violation
    for a number nobody wrote. The shapes are a digit straight after a letter
    (m2, s2) or after a hyphen that itself follows a letter (m-3, s-1); a real
    negative number is written with a space before the sign.
    """
    if start == 0:
        return False
    prev = text[start - 1]
    if prev.isalpha():
        return True
    return prev in "-^" and start >= 2 and text[start - 2].isalpha()


def _is_wordish(ch: str) -> bool:
    """Letter, digit, or a combining mark."""
    return ch.isalnum() or unicodedata.category(ch).startswith("M")


def _is_standalone(text: str, start: int, end: int) -> bool:
    """Is this match a whole word rather than a fragment of a longer one?

    Two failures make this necessary and rule out a plain \\b.

    Substrings: "height" contains "eight", "zone" contains "one", "often"
    contains "ten". Without a boundary the validator manufactures numbers out of
    ordinary words and then reports the narration for using them.

    Indic scripts: \\b does not work there. A Devanagari or Tamil word usually
    ends in a combining vowel sign — the au in नौ, the u in ஏழு — which is a mark,
    not a word character, so there is no \\w to \\W transition after it and \\b never
    matches. Treating marks as word-internal fixes both scripts at once.
    """
    before = text[start - 1] if start > 0 else " "
    after = text[end] if end < len(text) else " "
    return not _is_wordish(before) and not _is_wordish(after)


def _allowed_values(bundle: EvidenceBundle, narration: str = "") -> list[float]:
    """Bundle values, plus declared conversions the narration actually invokes.

    A conversion is only admitted when its target unit appears in the text. Left
    unconditional, every conversion widens the set of acceptable numbers whether
    or not the sentence is using it: 18 kt is 9.26 m/s, so "nine metres" would be
    accepted as a rounded m/s reading of a wind speed. Requiring the unit to be
    present is cheap and closes that.
    """
    text = narration.lower()
    allowed: list[float] = []
    for item in bundle.items:
        candidates = [item.value] + ([item.threshold] if item.threshold is not None else [])
        for value in candidates:
            allowed.append(value)
            for unit, factor, offset in DECLARED_CONVERSIONS.get(item.unit, []):
                if unit.lower() in text:
                    allowed.append(value * factor + offset)
    return allowed


def validate(
    narration: str,
    bundle: EvidenceBundle,
    *,
    language: str = "en",
    tolerance: float = DEFAULT_TOLERANCE,
    ignore_below: float = 0.0,
) -> FirewallResult:
    """Check that every number in the narration came from the bundle.

    Tolerance is relative for large values and absolute for small ones, so 2.43
    may be narrated as 2.4 and 1176.45 as 1176.5 without either being treated as
    invented.
    """
    numbers, unparsed = extract_numbers(narration, language)
    allowed = _allowed_values(bundle, narration)
    violations: list[Violation] = []
    checked: list[float] = []

    for token, value in numbers:
        checked.append(value)
        if abs(value) < ignore_below:
            continue
        if not _matches_any(value, allowed, tolerance):
            violations.append(
                Violation(
                    token, value, "not present in the evidence bundle or any declared conversion"
                )
            )

    return FirewallResult(
        passed=not violations and not unparsed,
        violations=violations,
        checked=checked,
        unparsed=unparsed,
    )


def _matches_any(value: float, allowed: list[float], tolerance: float) -> bool:
    """Does this number come from a bundle value, allowing for narration rounding?

    Rounding, not proximity. A relative band around every candidate is a net: at
    a 6% band, a candidate of 9.26 accepts anything from 8.7 to 9.8, and a
    fabricated figure that happens to land there is waved through. Instead the
    value must equal a candidate rounded to a precision narration would plausibly
    use, so 2.43 admits 2.4 and 2 but not 2.5.
    """
    for candidate in allowed:
        if abs(value - candidate) <= tolerance:
            return True
        for places in (0, 1, 2, 3):
            if abs(value - round(candidate, places)) <= 1e-9:
                return True
        # Significant figures too: a model writing narration may round 1176.45 to
        # 1180 rather than to a decimal place, and that is still not invention.
        for sig in (2, 3, 4, 5, 6):
            if candidate != 0 and abs(value - float(f"%.{sig}g" % candidate)) <= 1e-9:
                return True
    return False


STRICTER_PROMPT_SUFFIX = (
    "\n\nYour previous answer contained a number that is not in the evidence. "
    "Rewrite it using ONLY the numbers listed above, copied exactly. Do not round, "
    "do not convert units, and do not add any figure of your own."
)


def render_template(bundle: EvidenceBundle) -> str:
    """The fallback when validation fails twice.

    Built entirely from bundle rows, so it cannot fail its own check. Plain, but
    a plain true sentence beats a fluent invented one.
    """
    parts: list[str] = []
    if bundle.risk_class:
        parts.append(bundle.risk_class.replace("_", "-").upper())
    for item in bundle.items:
        # Two decimals, not :g. :g gives six significant figures, so a chlorophyll
        # of 1.1757048 renders as "1.1757" — which the matcher does not recognise
        # as any decimal rounding of the stored value, and the fallback fails its
        # own check. It is also what a person would read out loud.
        shown = f"{round(item.value, 2):g}"
        parts.append(f"{item.key.replace('_', ' ')} {shown} {item.unit}".strip())
    parts.append(bundle.notice)
    return ". ".join(parts)
