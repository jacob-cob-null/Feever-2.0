"""Parse PhilHealth Annex A & B PDFs into JSON lookup tables."""

import json
import re
import sys
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
POLICY_DIR = ROOT / "models" / "reserved" / "policies"
OUT_DIR = ROOT / "models" / "reserved"

ANNEX_A_PDF = POLICY_DIR / "AnnexA-ListofMedicalCaseRates.pdf"
ANNEX_B_PDF = POLICY_DIR / "AnnexB-ListofProcedureCaseRates.pdf"
ANNEX_A_JSON = OUT_DIR / "philhealth_annex_a.json"
ANNEX_B_JSON = OUT_DIR / "philhealth_annex_b.json"


def _parse_float(val: str | None) -> float | None:
    """Convert string like '11,700.00' to float."""
    if not val:
        return None
    cleaned = re.sub(r"[^\d.]", "", val.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


def _is_header_row(row: list) -> bool:
    """Detect table header rows to skip."""
    if not row or not row[0]:
        return False
    first = str(row[0]).strip().upper()
    return first in ("ICD CODE", "RVS CODE", "CODE", "FIRST CASE RATE")


def _extract_table(pdf_path: Path, code_label: str) -> list[dict]:
    """Extract all rows from a PhilHealth annex PDF.

    Args:
        pdf_path: Path to the PDF file.
        code_label: Key name for the code column ('icd_code' or 'rvs_code').

    Returns:
        List of dicts with keys: code, description, case_rate,
        hospital_share, professional_fee.
    """
    records = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables(
                table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "snap_tolerance": 5,
                }
            )
            for table in tables:
                for row in table:
                    if not row or len(row) < 5:
                        continue
                    # Skip header rows
                    if _is_header_row(row):
                        continue
                    # Skip sub-header "First Case Rate" spanning row
                    if row[0] and "FIRST CASE RATE" in str(row[0]).upper():
                        continue

                    code = (row[0] or "").strip()
                    # Collapse multi-line descriptions into single line
                    description = " ".join((row[1] or "").split())

                    # Some rows have merged header cells — skip if no code
                    if not code or not description:
                        continue
                    # Skip if the "code" cell looks like a sub-header
                    if code.upper() in ("CASE RATE", "HEALTH FACILITY FEE",
                                        "PROFESSIONAL FEE", "DESCRIPTION"):
                        continue

                    case_rate = _parse_float(row[2])
                    hospital_share = _parse_float(row[3])
                    professional_fee = _parse_float(row[4])

                    # Skip rows where all numeric fields are None (sub-headers)
                    if case_rate is None and hospital_share is None and professional_fee is None:
                        continue

                    records.append({
                        "code": code,
                        "description": description,
                        "case_rate": case_rate,
                        "hospital_share": hospital_share,
                        "professional_fee": professional_fee,
                    })

    return records


def main():
    errors = []
    if not ANNEX_A_PDF.exists():
        errors.append(f"Annex A not found: {ANNEX_A_PDF}")
    if not ANNEX_B_PDF.exists():
        errors.append(f"Annex B not found: {ANNEX_B_PDF}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        sys.exit(1)

    # --- Annex A (Medical Case Rates — ICD codes) ---
    print(f"Parsing Annex A ({ANNEX_A_PDF.name})...")
    annex_a = _extract_table(ANNEX_A_PDF, "icd_code")
    with open(ANNEX_A_JSON, "w", encoding="utf-8") as f:
        json.dump(annex_a, f, indent=2, ensure_ascii=False)
    print(f"  -> {len(annex_a)} records -> {ANNEX_A_JSON.name}")

    # --- Annex B (Procedure Case Rates — RVS codes) ---
    print(f"Parsing Annex B ({ANNEX_B_PDF.name})...")
    annex_b = _extract_table(ANNEX_B_PDF, "rvs_code")
    with open(ANNEX_B_JSON, "w", encoding="utf-8") as f:
        json.dump(annex_b, f, indent=2, ensure_ascii=False)
    print(f"  -> {len(annex_b)} records -> {ANNEX_B_JSON.name}")

    # Quick sanity check — print first 3 records from each
    print("\nAnnex A sample:")
    for r in annex_a[:3]:
        print(f"  {r['code']:15s} {r['case_rate']:>12,.2f}  {r['description'][:60]}")

    print("\nAnnex B sample:")
    for r in annex_b[:3]:
        print(f"  {r['code']:15s} {r['case_rate']:>12,.2f}  {r['description'][:60]}")


if __name__ == "__main__":
    main()
