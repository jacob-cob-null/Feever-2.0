"""Field-level confidence assessment for OCR extraction output."""

import re
from datetime import datetime


def assess_confidence(field: str, value) -> str | None:
    """Assign high/medium/low confidence to an extracted field value.

    Returns None if value is None (field not extracted).
    """
    if value is None:
        return None

    s = str(value).strip()
    if not s:
        return None

    assessor = _ASSESSORS.get(field, _default_assessor)
    return assessor(s)


# --- Per-field assessors ---

def _assess_date(s: str) -> str:
    # Try ISO parse
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.year < 2000 or dt > datetime.now().replace(year=datetime.now().year + 1):
                return "low"  # unreasonable date
            return "high"
        except ValueError:
            continue
    # Parseable but non-standard format
    if re.search(r"\d{4}", s):
        return "medium"
    return "low"


def _assess_patient_name(s: str) -> str:
    words = s.split()
    digit_ratio = sum(c.isdigit() for c in s) / max(len(s), 1)
    if digit_ratio > 0.3:
        return "low"  # too many digits for a name
    if len(words) >= 2:
        return "high"
    if len(words) == 1 and len(s) >= 2:
        return "medium"
    return "low"


def _assess_amount(s: str) -> str:
    # Strip currency symbols and commas
    cleaned = re.sub(r"[₱$,\s]", "", s)
    try:
        val = float(cleaned)
        if val < 0:
            return "low"
        if val == 0:
            return "medium"
        return "high"
    except ValueError:
        return "low"


def _assess_philhealth_number(s: str) -> str:
    # PhilHealth numbers are typically 12 digits with dashes: XX-XXXXXXXXX-X
    digits = re.sub(r"\D", "", s)
    if len(digits) == 12:
        return "high"
    if 8 <= len(digits) <= 14:
        return "medium"
    return "low"


def _assess_code(s: str) -> str:
    # ICD-10 or RVS codes — usually alphanumeric, 3-10 chars
    if len(s) < 2:
        return "low"
    if re.match(r"^[A-Z]\d{2}(\.\d{1,4})?$", s, re.IGNORECASE):
        return "high"  # looks like ICD-10
    if re.match(r"^[\d.]+$", s):
        return "high"  # looks like RVS numeric code
    if len(s) <= 20:
        return "medium"
    return "low"


def _assess_hospital_name(s: str) -> str:
    if len(s) < 3:
        return "low"
    if len(s.split()) >= 2:
        return "high"
    return "medium"


def _default_assessor(s: str) -> str:
    if len(s) >= 2:
        return "medium"
    return "low"


_ASSESSORS = {
    "date": _assess_date,
    "billing_date": _assess_date,
    "patient_name": _assess_patient_name,
    "hospital_name": _assess_hospital_name,
    "total_amount": _assess_amount,
    "philhealth_benefit": _assess_amount,
    "balance_due": _assess_amount,
    "tax_amount": _assess_amount,
    "philhealth_number": _assess_philhealth_number,
    "diagnosis_code": _assess_code,
    "procedure_code": _assess_code,
}
