"""Tests for 3-tier JSON parsing in ModelManager._parse_output()."""

import json

import pytest

from api.core.model import ModelManager


@pytest.fixture
def parser():
    return ModelManager._parse_output


class TestTier1CleanParse:
    def test_clean_json(self, parser, sample_ocr_output_json):
        result, tier = parser(sample_ocr_output_json)
        assert tier == 1
        assert result["patient_name"] == "Tan Chay Yee"
        assert result["total_amount"] == 193.00

    def test_null_fields(self, parser):
        text = '{"date": "2026-01-15", "patient_name": null, "total_amount": 100}'
        result, tier = parser(text)
        assert tier == 1
        assert result["patient_name"] is None
        assert result["total_amount"] == 100

    def test_minimal_json(self, parser):
        result, tier = parser('{"date": "2026-01-15"}')
        assert tier == 1
        assert result["date"] == "2026-01-15"


class TestTier2RepairParse:
    def test_markdown_fences(self, parser):
        text = '```json\n{"date": "2026-01-15", "total_amount": 193}\n```'
        result, tier = parser(text)
        assert tier == 2
        assert result["date"] == "2026-01-15"

    def test_trailing_comma(self, parser):
        text = '{"date": "2026-01-15", "total_amount": 193,}'
        result, tier = parser(text)
        assert tier == 2
        assert result["total_amount"] == 193

    def test_surrounding_text(self, parser):
        text = 'Here is the extracted data:\n{"date": "2026-01-15", "total_amount": 193}\nDone.'
        result, tier = parser(text)
        assert tier == 2
        assert result["date"] == "2026-01-15"

    def test_fences_with_trailing_comma(self, parser):
        text = '```\n{"date": "2026-01-15",}\n```'
        result, tier = parser(text)
        assert tier == 2

    def test_multiple_braces_falls_through(self, parser):
        # Greedy regex grabs first { to last }, which isn't valid JSON.
        # Falls to tier 3 regex extraction — this is correct behavior.
        text = 'Result: {"date": "2026-01-15"} extra {"ignore": true}'
        result, tier = parser(text)
        assert tier == 3
        assert result["date"] == "2026-01-15"


class TestTier3RegexExtraction:
    def test_broken_json_recoverable(self, parser):
        text = 'extracted "date": "2026-01-15" and "total_amount": 193 end'
        result, tier = parser(text)
        assert tier == 3
        assert result["date"] == "2026-01-15"
        assert result["total_amount"] == 193.0

    def test_partial_fields(self, parser):
        text = 'found "patient_name": "Tan Chay Yee" only'
        result, tier = parser(text)
        assert tier == 3
        assert result["patient_name"] == "Tan Chay Yee"

    def test_null_value_extraction(self, parser):
        text = '"date": "2026-01-15", "patient_name": null, broken json here'
        result, tier = parser(text)
        assert tier == 3
        assert result["date"] == "2026-01-15"
        assert result["patient_name"] is None

    def test_all_fields_recoverable(self, parser):
        text = (
            '"date": "2026-01-15", "patient_name": "Test", '
            '"philhealth_number": "12-345678901-2", '
            '"diagnosis_code": "N20.9", "procedure_code": "36100", '
            '"total_amount": 500, "philhealth_benefit": 200, '
            '"balance_due": 300 broken}'
        )
        result, tier = parser(text)
        assert tier == 3
        assert len(result) == 8


class TestParseFailure:
    def test_total_garbage(self, parser):
        with pytest.raises(ValueError, match="Could not extract"):
            parser("absolutely nothing useful here at all")

    def test_empty_string(self, parser):
        with pytest.raises((ValueError, json.JSONDecodeError)):
            parser("")

    def test_no_matching_fields(self, parser):
        with pytest.raises(ValueError):
            parser("some random text with no field patterns whatsoever")
