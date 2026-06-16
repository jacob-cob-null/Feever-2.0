"""Tests for field-level confidence assessment."""

import pytest

from api.core.confidence import assess_confidence


class TestDateConfidence:
    def test_valid_iso_date(self):
        assert assess_confidence("date", "2026-01-15") == "high"

    def test_valid_slash_date(self):
        assert assess_confidence("date", "01/15/2026") == "high"

    def test_future_date(self):
        assert assess_confidence("date", "2090-12-01") == "low"

    def test_ancient_date(self):
        assert assess_confidence("date", "1990-01-01") == "low"

    def test_partial_date(self):
        # Has a 4-digit year but doesn't parse cleanly
        assert assess_confidence("date", "Jan 2024") == "medium"

    def test_garbage_date(self):
        assert assess_confidence("date", "xyz") == "low"

    def test_none(self):
        assert assess_confidence("date", None) is None


class TestPatientNameConfidence:
    def test_full_name(self):
        assert assess_confidence("patient_name", "Tan Chay Yee") == "high"

    def test_two_words(self):
        assert assess_confidence("patient_name", "Juan Cruz") == "high"

    def test_single_word(self):
        assert assess_confidence("patient_name", "Juan") == "medium"

    def test_single_char(self):
        assert assess_confidence("patient_name", "X") == "low"

    def test_digit_heavy(self):
        assert assess_confidence("patient_name", "ABC123456") == "low"

    def test_none(self):
        assert assess_confidence("patient_name", None) is None


class TestAmountConfidence:
    def test_positive_amount(self):
        assert assess_confidence("total_amount", "193.00") == "high"

    def test_integer_amount(self):
        assert assess_confidence("total_amount", "5000") == "high"

    def test_with_currency(self):
        assert assess_confidence("total_amount", "₱193.00") == "high"

    def test_with_commas(self):
        assert assess_confidence("total_amount", "1,234.56") == "high"

    def test_zero(self):
        assert assess_confidence("total_amount", "0") == "medium"

    def test_negative(self):
        assert assess_confidence("total_amount", "-50") == "low"

    def test_not_a_number(self):
        assert assess_confidence("total_amount", "N/A") == "low"

    def test_none(self):
        assert assess_confidence("total_amount", None) is None

    def test_balance_due(self):
        assert assess_confidence("balance_due", "93.00") == "high"

    def test_philhealth_benefit(self):
        assert assess_confidence("philhealth_benefit", "100") == "high"


class TestPhilhealthNumberConfidence:
    def test_valid_12_digits(self):
        assert assess_confidence("philhealth_number", "21-210942992-0") == "high"

    def test_valid_no_dashes(self):
        assert assess_confidence("philhealth_number", "212109429920") == "high"

    def test_short_number(self):
        assert assess_confidence("philhealth_number", "12345678") == "medium"

    def test_too_short(self):
        assert assess_confidence("philhealth_number", "123") == "low"

    def test_none(self):
        assert assess_confidence("philhealth_number", None) is None


class TestCodeConfidence:
    def test_icd10_code(self):
        assert assess_confidence("diagnosis_code", "N20.9") == "high"

    def test_icd10_short(self):
        assert assess_confidence("diagnosis_code", "I10") == "high"

    def test_rvs_numeric(self):
        assert assess_confidence("procedure_code", "36100") == "high"

    def test_rvs_dotted(self):
        assert assess_confidence("procedure_code", "90.5.0.10") == "high"

    def test_short_code(self):
        assert assess_confidence("diagnosis_code", "A") == "low"

    def test_none(self):
        assert assess_confidence("diagnosis_code", None) is None


class TestHospitalNameConfidence:
    def test_full_name(self):
        assert assess_confidence("hospital_name", "Ospital ng Angeles") == "high"

    def test_short_name(self):
        assert assess_confidence("hospital_name", "OA") == "low"

    def test_single_word(self):
        assert assess_confidence("hospital_name", "Hospital") == "medium"

    def test_none(self):
        assert assess_confidence("hospital_name", None) is None
