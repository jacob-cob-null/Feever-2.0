"""Post-processing validation and normalization for OCR extraction output."""

import re
from datetime import datetime


def normalize_date(value: str | None) -> str | None:
    """Convert various date formats to ISO YYYY-MM-DD.

    Handles: "MAR 24, 2026", "01/15/2026", "2026-01-15", "24-Mar-2026", etc.
    Returns original string if parsing fails (let confidence handle the flag).
    """
    if not value:
        return None

    s = str(value).strip()

    # Already ISO
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s

    formats = [
        "%b %d, %Y",       # MAR 24, 2026
        "%B %d, %Y",       # March 24, 2026
        "%d-%b-%Y",        # 24-Mar-2026
        "%d %b %Y",        # 24 Mar 2026
        "%m/%d/%Y",        # 01/15/2026
        "%d/%m/%Y",        # 15/01/2026
        "%Y/%m/%d",        # 2026/01/15
        "%m-%d-%Y",        # 01-15-2026
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return s  # Return original if no format matches


def normalize_amount(value) -> float | None:
    """Clean and convert amount values to float.

    Strips currency symbols (₱, $, PHP), commas, and whitespace.
    Returns None if not a valid number.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()
    # Strip common currency prefixes/suffixes and commas
    s = re.sub(r"[₱$,\s]", "", s)
    s = re.sub(r"^PHP\s*", "", s, flags=re.IGNORECASE)
    try:
        return float(s)
    except ValueError:
        return None


def cross_validate(raw: dict, notes: list[str]) -> None:
    """Cross-validate extracted fields against each other.

    Adds warnings to notes list. Does not modify raw dict.
    """
    total = normalize_amount(raw.get("total_amount"))
    phil = normalize_amount(raw.get("philhealth_benefit"))
    balance = normalize_amount(raw.get("balance_due"))

    # Check: total ≈ philhealth_benefit + balance_due
    if total is not None and phil is not None and balance is not None:
        expected = phil + balance
        if total > 0 and abs(total - expected) > 1.0:
            notes.append(
                f"Cross-validation: total_amount ({total:.2f}) does not equal "
                f"philhealth_benefit ({phil:.2f}) + balance_due ({balance:.2f}) "
                f"= {expected:.2f} — review for accuracy"
            )

    # Check: line items sum ≈ total_amount
    line_items = raw.get("line_items")
    if isinstance(line_items, list) and len(line_items) > 0 and total is not None:
        items_sum = sum(
            normalize_amount(li.get("amount")) or 0
            for li in line_items
            if isinstance(li, dict)
        )
        if items_sum > 0 and total > 0 and abs(items_sum - total) > 1.0:
            notes.append(
                f"Cross-validation: line items sum ({items_sum:.2f}) does not "
                f"match total_amount ({total:.2f}) — review for missing items"
            )
