"""Shared fixtures for Fee-Ver 2.0 test suite."""

import pytest


@pytest.fixture
def sample_ocr_output():
    """Realistic model output dict (extended schema with line_items)."""
    return {
        "hospital_name": "Ospital ng Angeles",
        "date": "2026-01-15",
        "patient_name": "Tan Chay Yee",
        "philhealth_number": "21-210942992-0",
        "diagnosis_code": "N20.9",
        "procedure_code": "36100",
        "total_amount": 193.00,
        "philhealth_benefit": 100.00,
        "balance_due": 93.00,
        "line_items": [
            {"description": "Complete Blood Count", "amount": 250.00},
            {"description": "Urinalysis", "amount": 150.00},
        ],
    }


@pytest.fixture
def sample_ocr_output_json(sample_ocr_output):
    """The same output as a JSON string."""
    import json
    return json.dumps(sample_ocr_output)


@pytest.fixture
def sample_ocr_partial():
    """Model output with many null fields (out-of-domain document)."""
    return {
        "date": "15/01/2019",
        "patient_name": None,
        "philhealth_number": None,
        "diagnosis_code": None,
        "procedure_code": None,
        "total_amount": 193.00,
        "philhealth_benefit": None,
        "balance_due": None,
    }


@pytest.fixture
def valid_png_bytes():
    """Minimal valid 1x1 white PNG image."""
    from PIL import Image
    from io import BytesIO
    buf = BytesIO()
    Image.new("RGB", (100, 100), (255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def corrupted_bytes():
    """Bytes that are not a valid image."""
    return b"this is not an image file at all"
