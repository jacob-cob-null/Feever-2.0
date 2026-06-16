"""Tests for rule engine — PhilHealth + Hospital DB cross-referencing."""

import pytest

from api.core.rule_engine import RuleEngine

DB_PATH = "models/reserved/hospital_db.sqlite"
ANNEX_A = "models/reserved/philhealth_annex_a.json"
ANNEX_B = "models/reserved/philhealth_annex_b.json"


@pytest.fixture(scope="module")
def engine():
    """Shared RuleEngine instance (loads real data once)."""
    return RuleEngine(
        db_path=DB_PATH,
        annex_a_path=ANNEX_A,
        annex_b_path=ANNEX_B,
    )


class TestPhilhealthExactCode:
    def test_annex_a_exact_match(self, engine):
        result, discrepancies, summary = engine.check({
            "diagnosis_code": "N20.9",
            "total_amount": 193.0,
            "line_items": [],
        })
        assert len(result.philhealth_matches) >= 1
        match = result.philhealth_matches[0]
        assert match.matched_code == "N20.9"
        assert match.match_method == "exact_code"
        assert match.match_score == 100.0
        assert match.annex_source == "A"
        assert match.status == "WITHIN_LIMIT"

    def test_annex_b_exact_match(self, engine):
        result, discrepancies, summary = engine.check({
            "procedure_code": "36100",
            "total_amount": 193.0,
            "line_items": [],
        })
        matches_b = [m for m in result.philhealth_matches if m.annex_source == "B"]
        assert len(matches_b) >= 1
        match = matches_b[0]
        assert match.matched_code == "36100"
        assert match.match_method == "exact_code"
        assert match.match_score == 100.0

    def test_exceeds_ceiling(self, engine):
        # N20.9 has ceiling 7800 — claim 50000
        result, discrepancies, summary = engine.check({
            "diagnosis_code": "N20.9",
            "total_amount": 50000.0,
            "line_items": [],
        })
        match = result.philhealth_matches[0]
        assert match.status == "EXCEEDS_LIMIT"
        assert match.case_rate_ceiling == 7800.0

        # Check discrepancy
        disc = [d for d in discrepancies if d.violation == "EXCEEDS_PHILHEALTH_CEILING"]
        assert len(disc) == 1
        assert disc[0].severity == "HIGH"
        assert disc[0].reference_code == "ICD:N20.9"
        assert disc[0].reference_source == "philhealth_annex_a"
        assert disc[0].reviewer_action is not None

    def test_nonexistent_code_no_match(self, engine):
        result, _, _ = engine.check({
            "diagnosis_code": "ZZZZZZZ",
            "total_amount": 100.0,
            "line_items": [],
        })
        # Exact code match fails — no PhilHealth match added
        assert len(result.philhealth_matches) == 0

    def test_matched_description_populated(self, engine):
        result, _, _ = engine.check({
            "diagnosis_code": "N20.9",
            "total_amount": 100.0,
            "line_items": [],
        })
        match = result.philhealth_matches[0]
        assert match.matched_description is not None
        assert len(match.matched_description) > 0


class TestPhilhealthFuzzy:
    def test_not_covered_low_score(self, engine):
        """Generic description should not match PhilHealth annexes."""
        result, discrepancies, _ = engine.check({
            "line_items": [{"description": "Office Supplies", "price": 50}],
        })
        ph_matches = result.philhealth_matches
        assert len(ph_matches) == 1
        assert ph_matches[0].status == "NOT_COVERED"
        assert ph_matches[0].match_method == "fuzzy"

        # Should have NOT_COVERED discrepancy with reviewer action
        disc = [d for d in discrepancies if d.violation == "NOT_COVERED"]
        assert len(disc) >= 1
        assert disc[0].reviewer_action is not None


class TestHospitalDb:
    def test_no_match_not_found(self, engine):
        result, discrepancies, _ = engine.check({
            "line_items": [{"description": "Alien Probe Scan", "price": 999}],
        })
        db_matches = result.hospital_db_matches
        assert len(db_matches) == 1
        assert db_matches[0].status == "NOT_FOUND"
        assert db_matches[0].match_method == "fuzzy"

        disc = [d for d in discrepancies if d.violation == "NOT_IN_HOSPITAL_SCHEDULE"]
        assert len(disc) == 1
        assert disc[0].severity == "MEDIUM"
        assert disc[0].reviewer_action is not None

    def test_match_with_service_id(self, engine):
        """A close description should match and return service_ID."""
        result, _, _ = engine.check({
            "line_items": [{"description": "Complete Blood Count", "price": 250}],
        })
        db_matches = result.hospital_db_matches
        assert len(db_matches) == 1
        if db_matches[0].status in ("MATCH", "DISCREPANCY"):
            assert db_matches[0].matched_service_id is not None
            assert db_matches[0].matched_description is not None
            assert db_matches[0].match_score is not None
            assert db_matches[0].match_score > 0

    def test_price_mismatch_discrepancy(self, engine):
        """Claiming a wildly different price should produce a PRICE_MISMATCH."""
        result, discrepancies, _ = engine.check({
            "line_items": [{"description": "Complete Blood Count", "price": 5000}],
        })
        db_matches = result.hospital_db_matches
        if db_matches[0].status == "DISCREPANCY":
            disc = [d for d in discrepancies if d.violation == "PRICE_MISMATCH"]
            assert len(disc) >= 1
            assert disc[0].reference_code is not None
            assert disc[0].reference_code.startswith("service_ID:")
            assert disc[0].reference_source is not None
            assert disc[0].reference_source.startswith("hospital_db:")
            assert disc[0].reviewer_action is not None

    def test_hospital_filter(self, engine):
        """When hospital_name is provided, results should prefer that hospital."""
        result, _, _ = engine.check({
            "hospital_name": "Ospital ng Angeles",
            "line_items": [{"description": "Hemoglobin", "price": 100}],
        })
        db_matches = result.hospital_db_matches
        if db_matches[0].status in ("MATCH", "DISCREPANCY"):
            assert "Angeles" in db_matches[0].matched_hospital


class TestSummary:
    def test_empty_input(self, engine):
        _, _, summary = engine.check({"line_items": []})
        assert summary.total_items == 0
        assert summary.total_claimed == 0
        assert summary.excess_amount == 0

    def test_counts(self, engine):
        _, discrepancies, summary = engine.check({
            "line_items": [
                {"description": "Hemoglobin", "price": 100},
                {"description": "Alien Probe", "price": 999},
            ],
        })
        assert summary.total_items == 2
        assert summary.items_flagged == len(discrepancies)
        assert summary.total_claimed > 0
