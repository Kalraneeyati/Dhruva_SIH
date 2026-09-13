"""Adversarial cases for the numeric firewall — IMPLEMENTATION.md 3.3 names
these exact four cases: "an injected fabricated wave height, a hallucinated
distance, a converted unit that was not declared, a Tamil numeral."
"""

from __future__ import annotations

import datetime as dt

from dhruva.evidence.firewall import extract_numbers, render_template, validate_narration
from dhruva.evidence.schema import EvidenceBundleEntry

NOW = dt.datetime.now(dt.UTC)


def _bundle(**kwargs) -> list[EvidenceBundleEntry]:
    return [
        EvidenceBundleEntry(key=k, value=v, unit="m", dataset_id="test", cell_lat=0, cell_lon=0, valid_time=NOW)
        for k, v in kwargs.items()
    ]


def test_a_true_value_passes():
    bundle = _bundle(wave_height=2.3)
    result = validate_narration("Wave height is 2.3 m.", bundle)
    assert result.ok


def test_catches_an_injected_fabricated_wave_height():
    bundle = _bundle(wave_height=2.3)
    result = validate_narration("Wave height is 9.9 m, dangerously high.", bundle)
    assert not result.ok
    assert 9.9 in result.violations


def test_catches_a_hallucinated_distance():
    bundle = _bundle(wave_height=2.3)
    result = validate_narration("The nearest fishing zone is 47 nautical miles away.", bundle)
    assert not result.ok
    assert 47.0 in result.violations


def test_allows_a_declared_unit_conversion_but_not_an_undeclared_one():
    bundle = _bundle(wave_height=1.0)  # 1 m
    # Declared conversion: m -> ft (3.28084). 1m = 3.28ft, should pass.
    converted = validate_narration("Wave height is about 3.28 ft.", bundle)
    assert converted.ok

    # An arbitrary, undeclared "conversion" (e.g. a wrong factor) must still fail.
    undeclared = validate_narration("Wave height is about 100 fathoms.", bundle)
    assert not undeclared.ok


def test_catches_a_hallucinated_number_written_as_a_tamil_numeral():
    bundle = _bundle(wave_height=2.3)
    # ௯.9 not on the bundle — Tamil digit ௯ (9) followed by ASCII ".9" is an
    # edge case; use a pure Tamil-digit fabrication instead: ௯௦ (90).
    narrative = "அலை உயரம் ௯0 மீட்டர் ஆகும்."  # "wave height is 90 metres" — fabricated
    result = validate_narration(narrative, bundle)
    assert not result.ok
    assert 90.0 in result.violations


def test_extract_numbers_reads_devanagari_digits():
    assert extract_numbers("लहर की ऊँचाई १.५ मीटर") == [1.5]


def test_extract_numbers_reads_tamil_digits():
    assert extract_numbers("அலை உயரம் ௨.௫ மீட்டர்") == [2.5]


def test_small_integer_counts_in_prose_are_not_flagged_as_measurements():
    bundle = _bundle(wave_height=2.3)
    result = validate_narration("This covers 2 of the 8 official queries.", bundle)
    assert result.ok  # "2" and "8" are small counts, not fabricated measurements


def test_render_template_cannot_introduce_a_number_not_in_values():
    text = render_template("Wave height {wave_height} m, wind {wind_speed} kt.", {"wave_height": "2.3", "wind_speed": "18"})
    assert text == "Wave height 2.3 m, wind 18 kt."
    # Any key not supplied is left as the literal placeholder, never guessed.
    text2 = render_template("Gust {gust} kt.", {})
    assert text2 == "Gust {gust} kt."
