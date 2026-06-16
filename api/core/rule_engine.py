"""Hospital DB + PhilHealth Annex A/B rule engine (Phase 4b — transparent matching)."""

import json
import logging
import re
import sqlite3
from pathlib import Path

from rapidfuzz import fuzz

from api.schemas.response import (
    Discrepancy,
    HospitalDbMatch,
    PhilhealthMatch,
    RuleEngineResult,
    Summary,
)

logger = logging.getLogger(__name__)

# Thresholds (overridable via env)
HOSPITAL_FUZZY_THRESHOLD = 80
PHILHEALTH_FUZZY_THRESHOLD = 82
PRICE_DELTA_TOLERANCE = 0.05  # 5%

# Severity mapping
SEVERITY = {
    "EXCEEDS_PHILHEALTH_CEILING": "HIGH",
    "PRICE_MISMATCH_HIGH": "HIGH",
    "PRICE_MISMATCH_MEDIUM": "MEDIUM",
    "DUPLICATE_CHARGE": "HIGH",
    "NOT_IN_HOSPITAL_SCHEDULE": "MEDIUM",
    "NOT_COVERED": "LOW",
}


def _normalize_text(s: str) -> str:
    """Uppercase, strip punctuation, collapse whitespace."""
    s = s.upper()
    s = re.sub(r"[^\w\s]", " ", s)
    return " ".join(s.split())


class RuleEngine:
    """Cross-references OCR output against hospital DB and PhilHealth rules."""

    def __init__(
        self,
        db_path: str | Path,
        annex_a_path: str | Path,
        annex_b_path: str | Path,
        hospital_threshold: float = HOSPITAL_FUZZY_THRESHOLD,
        philhealth_threshold: float = PHILHEALTH_FUZZY_THRESHOLD,
        price_tolerance: float = PRICE_DELTA_TOLERANCE,
    ):
        self.db_path = str(db_path)
        self.hospital_threshold = hospital_threshold
        self.philhealth_threshold = philhealth_threshold
        self.price_tolerance = price_tolerance

        # Load PhilHealth annexes into memory
        with open(annex_a_path, encoding="utf-8") as f:
            self.annex_a: list[dict] = json.load(f)
        with open(annex_b_path, encoding="utf-8") as f:
            self.annex_b: list[dict] = json.load(f)

        # Pre-normalize descriptions for fuzzy matching
        self._annex_a_norm = [
            (_normalize_text(r["description"]), r) for r in self.annex_a
        ]
        self._annex_b_norm = [
            (_normalize_text(r["description"]), r) for r in self.annex_b
        ]

        # Validate DB
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        self.db_record_count = conn.execute(
            "SELECT COUNT(*) FROM medical_services"
        ).fetchone()[0]
        conn.close()

        logger.info(
            "RuleEngine loaded: %d hospital records, %d annex A, %d annex B",
            self.db_record_count,
            len(self.annex_a),
            len(self.annex_b),
        )

    def check(self, ocr: dict) -> tuple[RuleEngineResult, list[Discrepancy], Summary]:
        """Run all checks against OCR output.

        Args:
            ocr: Dict with keys from the extraction schema (date, patient_name,
                 total_amount, diagnosis_code, procedure_code, etc.)

        Returns:
            (rule_engine_result, discrepancies, summary)
        """
        line_items = ocr.get("line_items", [])
        hospital_name = ocr.get("hospital_name")
        diagnosis_code = ocr.get("diagnosis_code")
        procedure_code = ocr.get("procedure_code")
        total_amount = ocr.get("total_amount")

        ph_matches = []
        db_matches = []
        discrepancies = []

        # --- PhilHealth checks ---
        # Check by diagnosis code against Annex A
        if diagnosis_code:
            ph_match = self._check_philhealth_by_code(
                diagnosis_code, total_amount, self.annex_a, "A"
            )
            if ph_match:
                ph_matches.append(ph_match)
                disc = self._philhealth_discrepancy(ph_match)
                if disc:
                    discrepancies.append(disc)

        # Check by procedure code against Annex B
        if procedure_code:
            ph_match = self._check_philhealth_by_code(
                procedure_code, total_amount, self.annex_b, "B"
            )
            if ph_match:
                ph_matches.append(ph_match)
                disc = self._philhealth_discrepancy(ph_match)
                if disc:
                    discrepancies.append(disc)

        # Fuzzy-match line items against both annexes
        for item in line_items:
            desc = item.get("description", "")
            price = item.get("price") or 0
            ph_match = self._fuzzy_philhealth(desc, price)
            if ph_match:
                ph_matches.append(ph_match)
                disc = self._philhealth_discrepancy(ph_match)
                if disc:
                    discrepancies.append(disc)

        # --- Hospital DB checks ---
        for item in line_items:
            desc = item.get("description", "")
            price = item.get("price") or 0
            db_match = self._check_hospital_db(desc, price, hospital_name)
            db_matches.append(db_match)
            disc = self._hospital_discrepancy(db_match)
            if disc:
                discrepancies.append(disc)

        # --- Summary ---
        total_items = len(line_items)
        items_matched = sum(1 for m in db_matches if m.status == "MATCH")
        items_flagged = len(discrepancies)
        total_claimed = sum((it.get("price") or 0) for it in line_items)
        total_allowable = sum(
            m.reference_price for m in db_matches if m.status == "MATCH"
        )
        excess = max(0, total_claimed - total_allowable)

        return (
            RuleEngineResult(
                philhealth_matches=ph_matches,
                hospital_db_matches=db_matches,
            ),
            discrepancies,
            Summary(
                total_items=total_items,
                items_matched=items_matched,
                items_flagged=items_flagged,
                total_claimed=round(total_claimed, 2),
                total_allowable=round(total_allowable, 2),
                excess_amount=round(excess, 2),
            ),
        )

    # --- PhilHealth helpers ---

    def _check_philhealth_by_code(
        self, code: str, amount: float | None, annex: list[dict], source: str
    ) -> PhilhealthMatch | None:
        """Exact code match against an annex."""
        code_upper = code.strip().upper()
        for entry in annex:
            if entry["code"].strip().upper() == code_upper:
                claimed = amount or 0
                ceiling = entry["case_rate"] or 0
                status = (
                    "WITHIN_LIMIT" if claimed <= ceiling else "EXCEEDS_LIMIT"
                )
                return PhilhealthMatch(
                    item=entry["description"],
                    claimed_amount=claimed,
                    annex_source=source,
                    matched_code=entry["code"],
                    matched_description=entry["description"],
                    case_rate_ceiling=ceiling,
                    hospital_share=entry.get("hospital_share", 0) or 0,
                    professional_fee=entry.get("professional_fee", 0) or 0,
                    status=status,
                    match_score=100.0,
                    match_method="exact_code",
                )
        return None

    def _fuzzy_philhealth(
        self, description: str, claimed: float
    ) -> PhilhealthMatch | None:
        """Fuzzy-match a line item description against Annex A then B."""
        norm = _normalize_text(description)
        if not norm:
            return None

        best_score = 0
        best_entry = None
        best_source = "A"

        for norm_desc, entry in self._annex_a_norm:
            score = fuzz.token_sort_ratio(norm, norm_desc)
            if score > best_score:
                best_score = score
                best_entry = entry
                best_source = "A"

        for norm_desc, entry in self._annex_b_norm:
            score = fuzz.token_sort_ratio(norm, norm_desc)
            if score > best_score:
                best_score = score
                best_entry = entry
                best_source = "B"

        if best_score < self.philhealth_threshold or best_entry is None:
            return PhilhealthMatch(
                item=description,
                claimed_amount=claimed,
                annex_source="N/A",
                matched_code=None,
                matched_description=None,
                case_rate_ceiling=0,
                hospital_share=0,
                professional_fee=0,
                status="NOT_COVERED",
                match_score=round(best_score, 1) if best_entry else None,
                match_method="fuzzy",
            )

        ceiling = best_entry["case_rate"] or 0
        status = "WITHIN_LIMIT" if claimed <= ceiling else "EXCEEDS_LIMIT"
        return PhilhealthMatch(
            item=description,
            claimed_amount=claimed,
            annex_source=best_source,
            matched_code=best_entry["code"],
            matched_description=best_entry["description"],
            case_rate_ceiling=ceiling,
            hospital_share=best_entry.get("hospital_share", 0) or 0,
            professional_fee=best_entry.get("professional_fee", 0) or 0,
            status=status,
            match_score=round(best_score, 1),
            match_method="fuzzy",
        )

    @staticmethod
    def _philhealth_discrepancy(match: PhilhealthMatch) -> Discrepancy | None:
        if match.status == "EXCEEDS_LIMIT":
            excess = match.claimed_amount - match.case_rate_ceiling
            # Build reference code from matched code
            code_prefix = "ICD" if match.annex_source == "A" else "RVS"
            ref_code = f"{code_prefix}:{match.matched_code}" if match.matched_code else None
            ref_source = f"philhealth_annex_{match.annex_source.lower()}" if match.annex_source != "N/A" else None
            return Discrepancy(
                item=match.item,
                claimed_amount=match.claimed_amount,
                violation="EXCEEDS_PHILHEALTH_CEILING",
                detail=(
                    f"Claimed {match.claimed_amount:,.2f} exceeds "
                    f"PhilHealth ceiling of {match.case_rate_ceiling:,.2f} "
                    f"by {excess:,.2f} (Annex {match.annex_source}"
                    f", code {match.matched_code})"
                    if match.matched_code
                    else f"Claimed {match.claimed_amount:,.2f} exceeds "
                    f"PhilHealth ceiling of {match.case_rate_ceiling:,.2f} "
                    f"by {excess:,.2f} (Annex {match.annex_source})"
                ),
                severity="HIGH",
                reference_code=ref_code,
                reference_source=ref_source,
                reviewer_action=(
                    f"Verify if the total claimed amount of {match.claimed_amount:,.2f} "
                    f"is correct. PhilHealth case rate ceiling for "
                    f"{match.matched_description or match.item} is {match.case_rate_ceiling:,.2f}. "
                    f"The excess of {excess:,.2f} may be the patient's responsibility."
                ),
            )
        if match.status == "NOT_COVERED":
            return Discrepancy(
                item=match.item,
                claimed_amount=match.claimed_amount,
                violation="NOT_COVERED",
                detail=f"'{match.item}' not found in PhilHealth Annex A or B",
                severity="LOW",
                reference_code=None,
                reference_source=None,
                reviewer_action=(
                    f"'{match.item}' did not match any PhilHealth case rate code "
                    f"(best fuzzy score: {match.match_score:.0f}/100). "
                    f"Check if a different service description or code applies."
                    if match.match_score is not None
                    else f"'{match.item}' did not match any PhilHealth case rate code. "
                    f"Check if a different service description or code applies."
                ),
            )
        return None

    # --- Hospital DB helpers ---

    def _check_hospital_db(
        self, description: str, claimed: float, hospital_name: str | None
    ) -> HospitalDbMatch:
        """Fuzzy-match a line item against hospital services."""
        norm = _normalize_text(description)
        if not norm:
            return HospitalDbMatch(
                item=description,
                claimed_amount=claimed,
                reference_price=0,
                matched_hospital="",
                matched_service_id=None,
                matched_description=None,
                delta_percent=0,
                status="NOT_FOUND",
                match_score=None,
                match_method="fuzzy",
            )

        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        try:
            if hospital_name:
                rows = conn.execute(
                    "SELECT service_ID, service_Name, service_Price, service_Origin "
                    "FROM medical_services WHERE service_Origin LIKE ?",
                    (f"%{hospital_name}%",),
                ).fetchall()
                # Fall back to all records if hospital filter yields nothing
                if not rows:
                    rows = conn.execute(
                        "SELECT service_ID, service_Name, service_Price, service_Origin "
                        "FROM medical_services"
                    ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT service_ID, service_Name, service_Price, service_Origin "
                    "FROM medical_services"
                ).fetchall()
        finally:
            conn.close()

        best_score = 0
        best_row = None
        for sid, name, price, origin in rows:
            score = fuzz.token_sort_ratio(norm, _normalize_text(name))
            if score > best_score:
                best_score = score
                best_row = (sid, name, price, origin)

        if best_score < self.hospital_threshold or best_row is None:
            return HospitalDbMatch(
                item=description,
                claimed_amount=claimed,
                reference_price=0,
                matched_hospital="",
                matched_service_id=None,
                matched_description=None,
                delta_percent=0,
                status="NOT_FOUND",
                match_score=round(best_score, 1) if best_row else None,
                match_method="fuzzy",
            )

        sid, name, ref_price, origin = best_row
        if ref_price > 0:
            delta = (claimed - ref_price) / ref_price
        else:
            delta = 0

        if abs(delta) <= self.price_tolerance:
            status = "MATCH"
        else:
            status = "DISCREPANCY"

        return HospitalDbMatch(
            item=description,
            claimed_amount=claimed,
            reference_price=ref_price,
            matched_hospital=origin,
            matched_service_id=sid,
            matched_description=name,
            delta_percent=round(delta * 100, 2),
            status=status,
            match_score=round(best_score, 1),
            match_method="fuzzy",
        )

    @staticmethod
    def _hospital_discrepancy(match: HospitalDbMatch) -> Discrepancy | None:
        if match.status == "NOT_FOUND":
            return Discrepancy(
                item=match.item,
                claimed_amount=match.claimed_amount,
                violation="NOT_IN_HOSPITAL_SCHEDULE",
                detail=f"'{match.item}' not found in hospital service schedule",
                severity="MEDIUM",
                reference_code=None,
                reference_source=None,
                reviewer_action=(
                    f"'{match.item}' did not match any hospital service "
                    f"(best fuzzy score: {match.match_score:.0f}/100). "
                    f"Verify the service description against the hospital's official rate schedule."
                    if match.match_score is not None
                    else f"'{match.item}' did not match any hospital service. "
                    f"Verify the service description against the hospital's official rate schedule."
                ),
            )
        if match.status == "DISCREPANCY":
            abs_delta = abs(match.delta_percent)
            severity = "HIGH" if abs_delta > 20 else "MEDIUM"
            ref_code = f"service_ID:{match.matched_service_id}" if match.matched_service_id else None
            ref_source = f"hospital_db:{match.matched_hospital}" if match.matched_hospital else None
            return Discrepancy(
                item=match.item,
                claimed_amount=match.claimed_amount,
                violation="PRICE_MISMATCH",
                detail=(
                    f"Claimed {match.claimed_amount:,.2f} vs reference "
                    f"{match.reference_price:,.2f} at {match.matched_hospital} "
                    f"({match.delta_percent:+.1f}%)"
                ),
                severity=severity,
                reference_code=ref_code,
                reference_source=ref_source,
                reviewer_action=(
                    f"Verify if the {abs_delta:.1f}% price difference for "
                    f"'{match.matched_description or match.item}' "
                    f"(service_ID {match.matched_service_id}) "
                    f"reflects an updated hospital rate schedule or a billing error. "
                    f"Match confidence: {match.match_score}/100."
                ),
            )
        return None
