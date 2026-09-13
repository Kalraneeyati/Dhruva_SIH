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


def test_a_negative_value_in_the_narrative_matches_its_negative_evidence():
    """Regression: extract_numbers used to discard the sign, so a cooling
    trend narrated as "-1.5C" extracted the unsigned 1.5, which could never
    match an evidence value of -1.5 and would wrongly withhold a correct
    answer. Found while wiring the real SST-trend handler."""
    bundle = _bundle(sst_change_c=-1.5)
    result = validate_narration("SST has fallen by -1.5 degC over six weeks.", bundle)
    assert result.ok


def test_a_positive_signed_value_also_matches():
    bundle = _bundle(sst_change_pct=3.2)
    result = validate_narration("That is +3.2% warmer than six weeks ago.", bundle)
    assert result.ok


def test_hyphen_in_a_compound_word_is_not_mistaken_for_a_minus_sign():
    bundle = _bundle(wave_height=2.3, valid_hours=12)
    # "sea-state" and "12-hour" contain hyphens that are not minus signs; the
    # "-" before "hour" must not be read as turning 12 negative (it would
    # then fail to match the positive valid_hours=12 evidence).
    result = validate_narration("Wave height is 2.3 m in this sea-state, valid for the next 12-hour window.", bundle)
    assert -12.0 not in result.checked
    assert result.ok


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
