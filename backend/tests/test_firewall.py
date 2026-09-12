"""Adversarial tests for the numeric firewall.

Gate 3 requires CI to fail when a fabricated number is injected into narration,
so these are written as attacks rather than as happy paths. The plan is blunt
about it: skipping these is "the one thing that makes the whole pitch collapse
under a judge's question."
"""

import datetime as dt

import pytest

from dhruva.evidence.firewall import (
    extract_numbers,
    render_template,
    transliterate_digits,
    validate,
)
from dhruva.evidence.schema import EvidenceBundle, EvidenceItem

NOW = dt.datetime(2026, 9, 12, 6, 0, tzinfo=dt.UTC)


def _bundle() -> EvidenceBundle:
    return EvidenceBundle(
        items=[
            EvidenceItem(
                key="wave_height",
                value=2.43,
                unit="m",
                dataset_id="open_meteo_marine",
                cell="11.0500N, 79.9500E",
                valid_time=NOW,
                threshold=2.0,
                rule_id="WAVE-C2",
            ),
            EvidenceItem(
                key="wind_speed",
                value=18.0,
                unit="kt",
                dataset_id="open_meteo_forecast",
                cell="11.0721N, 79.7782E",
                valid_time=NOW,
            ),
            EvidenceItem(
                key="current_speed",
                value=0.8,
                unit="kt",
                dataset_id="copernicus_phy_hourly",
                cell="11.0833N, 79.9167E",
            ),
        ],
        risk_class="caution",
        fired_rules=["WAVE-C2"],
    )


class TestFabricatedNumbers:
    def test_an_invented_wave_height_is_caught(self):
        """The attack the whole mechanism exists to stop."""
        r = validate("Waves are 3.8 m today.", _bundle())
        assert not r.passed
        assert any(v.value == pytest.approx(3.8) for v in r.violations)

    def test_a_hallucinated_distance_is_caught(self):
        r = validate("The fishing zone is 47 nautical miles southwest.", _bundle())
        assert not r.passed

    def test_a_real_value_passes(self):
        r = validate("Wave height is 2.43 m and wind is 18 kt.", _bundle())
        assert r.passed, r.messages

    def test_a_rounded_real_value_passes(self):
        """Narration says 2.4 for 2.43; that is rounding, not invention."""
        assert validate("Waves around 2.4 m.", _bundle()).passed

    def test_a_threshold_from_the_bundle_may_be_quoted(self):
        assert validate("Caution because 2.43 m is above the 2.0 m limit.", _bundle()).passed

    def test_one_real_number_does_not_launder_an_invented_one(self):
        r = validate("Wind is 18 kt and waves are 5.5 m.", _bundle())
        assert not r.passed
        assert len(r.violations) == 1


class TestUnitConversions:
    def test_a_declared_conversion_is_allowed(self):
        """2.43 m is 7.97 ft. Not a fabrication."""
        assert validate("Waves about 7.97 ft.", _bundle()).passed

    def test_kt_to_kmh_is_allowed(self):
        """18 kt is 33.3 km/h."""
        assert validate("Wind near 33.3 km/h.", _bundle()).passed

    def test_an_undeclared_conversion_is_rejected(self):
        """Wave height in fathoms is not a declared conversion, so 1.33 is
        indistinguishable from an invented number and must be refused."""
        r = validate("Waves about 1.33 fathoms.", _bundle())
        assert not r.passed


class TestNonAsciiDigits:
    def test_tamil_digits_transliterate(self):
        assert transliterate_digits("௨.௪௩") == "2.43"

    def test_devanagari_digits_transliterate(self):
        assert transliterate_digits("१८") == "18"

    def test_a_fabricated_number_in_tamil_digits_is_caught(self):
        """A firewall that only reads ASCII has a door in it."""
        r = validate("அலை உயரம் ௫.௫ மீட்டர்.", _bundle(), language="ta")
        assert not r.passed
        assert any(v.value == pytest.approx(5.5) for v in r.violations)

    def test_a_real_number_in_tamil_digits_passes(self):
        assert validate("அலை உயரம் ௨.௪௩ மீட்டர்.", _bundle(), language="ta").passed


class TestSpelledOutNumerals:
    def test_a_spelled_out_english_numeral_is_extracted(self):
        found, _ = extract_numbers("waves of five metres", "en")
        assert any(v == 5.0 for _, v in found)

    def test_a_fabricated_spelled_out_number_is_caught(self):
        """The most dangerous miss: a digit-only regex sees nothing, but the
        sentence still reads like a measurement."""
        r = validate("Waves of five metres today.", _bundle())
        assert not r.passed

    def test_a_fabricated_tamil_word_numeral_is_caught(self):
        r = validate("அலை ஏழு மீட்டர்.", _bundle(), language="ta")
        assert not r.passed

    def test_a_fabricated_hindi_word_numeral_is_caught(self):
        r = validate("लहरें नौ मीटर।", _bundle(), language="hi")
        assert not r.passed


class TestBoundaries:
    def test_narration_with_no_numbers_passes(self):
        assert validate("Conditions are calm. Return before evening.", _bundle()).passed

    def test_an_empty_bundle_rejects_any_number(self):
        r = validate("Waves are 2.0 m.", EvidenceBundle())
        assert not r.passed

    def test_a_digit_inside_a_unit_is_not_a_measurement(self):
        """Chlorophyll is quoted in "mg m-3"; the 3 is an exponent. Reading it as
        a number makes every narration that names the unit report a violation for
        something nobody wrote."""
        found, _ = extract_numbers("chlorophyll 1.18 mg m-3", "en")
        assert [v for _, v in found] == [1.18]

    def test_a_squared_unit_is_not_a_measurement(self):
        found, _ = extract_numbers("gust 12 m/s2", "en")
        assert [v for _, v in found] == [12.0]

    def test_a_thousands_separator_is_parsed_as_one_number(self):
        found, _ = extract_numbers("1,176 metres", "en")
        assert (1176.0) in [v for _, v in found]


class TestFallback:
    def test_the_template_is_built_only_from_bundle_rows(self):
        """The fallback must pass its own check, or the failure path is a second
        way to ship an unvalidated number."""
        bundle = _bundle()
        text = render_template(bundle)
        assert validate(text, bundle).passed, validate(text, bundle).messages

    def test_the_template_carries_the_advisory_notice(self):
        assert "INCOIS" in render_template(_bundle())


class TestTemplateWithRealValues:
    """The tidy fixture above hides a failure mode: real observations are messy
    floats, and a template that prints them at a precision the matcher does not
    recognise fails its own check — which would make the failure path a second
    way to ship an unvalidated number."""

    def test_the_template_passes_with_unrounded_observation_values(self):
        bundle = EvidenceBundle(
            items=[
                EvidenceItem(
                    key="chlorophyll",
                    value=1.1757048,
                    unit="mg m-3",
                    dataset_id="copernicus_bgc_pft",
                    cell="11.0N, 80.0E",
                ),
                EvidenceItem(
                    key="current_direction",
                    value=3.2749106,
                    unit="degree",
                    dataset_id="copernicus_phy_hourly",
                    cell="11.08N, 79.92E",
                ),
                EvidenceItem(
                    key="current_speed",
                    value=0.44702481,
                    unit="kt",
                    dataset_id="copernicus_phy_hourly",
                    cell="11.08N, 79.92E",
                ),
            ],
            risk_class="safe",
        )
        text = render_template(bundle)
        result = validate(text, bundle)
        assert result.passed, result.messages
