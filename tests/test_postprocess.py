"""Tests for post-processing validation and normalization."""

import pytest

from api.core.postprocess import cross_validate, normalize_amount, normalize_date


class TestNormalizeDate:
    def test_iso_passthrough(self):
        assert normalize_date("2026-01-15") == "2026-01-15"

    def test_month_name_format(self):
        assert normalize_date("MAR 24, 2026") == "2026-03-24"

    def test_full_month_name(self):
        assert normalize_date("March 24, 2026") == "2026-03-24"

    def test_slash_format(self):
        assert normalize_date("01/15/2026") == "2026-01-15"

    def test_dash_month_format(self):
        assert normalize_date("24-Mar-2026") == "2026-03-24"

    def test_none(self):
        assert normalize_date(None) is None

    def test_empty(self):
        assert normalize_date("") is None

    def test_unparseable_returned_as_is(self):
        assert normalize_date("sometime in January") == "sometime in January"


class TestNormalizeAmount:
    def test_float_passthrough(self):
        assert normalize_amount(193.0) == 193.0

    def test_int_passthrough(self):
        assert normalize_amount(5000) == 5000.0

    def test_string_number(self):
        assert normalize_amount("193.00") == 193.0

    def test_currency_peso(self):
        assert normalize_amount("₱1,234.56") == 1234.56

    def test_currency_dollar(self):
        assert normalize_amount("$500") == 500.0

    def test_php_prefix(self):
        assert normalize_amount("PHP 1000") == 1000.0

    def test_none(self):
        assert normalize_amount(None) is None

    def test_garbage(self):
        assert normalize_amount("N/A") is None


class TestCrossValidate:
    def test_matching_totals_no_note(self):
        notes = []
        cross_validate({
            "total_amount": 193.0,
            "philhealth_benefit": 100.0,
            "balance_due": 93.0,
        }, notes)
        assert not any("Cross-validation" in n for n in notes)

    def test_mismatched_totals_adds_note(self):
        notes = []
        cross_validate({
            "total_amount": 500.0,
            "philhealth_benefit": 100.0,
            "balance_due": 93.0,
        }, notes)
        assert any("total_amount" in n and "Cross-validation" in n for n in notes)

    def test_line_items_sum_mismatch(self):
        notes = []
        cross_validate({
            "total_amount": 1000.0,
            "line_items": [
                {"description": "A", "amount": 200},
                {"description": "B", "amount": 300},
            ],
        }, notes)
        assert any("line items sum" in n for n in notes)

    def test_line_items_sum_matches(self):
        notes = []
        cross_validate({
            "total_amount": 500.0,
            "line_items": [
                {"description": "A", "amount": 200},
                {"description": "B", "amount": 300},
            ],
        }, notes)
        assert not any("line items sum" in n for n in notes)

    def test_missing_fields_no_crash(self):
        notes = []
        cross_validate({}, notes)
        assert len(notes) == 0
