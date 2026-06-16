"""Integration tests for POST /analyze endpoint.

Uses a mocked ModelManager to avoid GPU dependency.
Tests the full HTTP request/response cycle through FastAPI.
"""

from io import BytesIO
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image


@pytest.fixture
def sample_model_output():
    """Realistic (dict, raw_text, parse_tier) return from run_inference."""
    return (
        {
            "date": "2026-01-15",
            "patient_name": "Tan Chay Yee",
            "philhealth_number": "21-210942992-0",
            "diagnosis_code": "N20.9",
            "procedure_code": "36100",
            "total_amount": 193.00,
            "philhealth_benefit": 100.00,
            "balance_due": 93.00,
        },
        '{"date":"2026-01-15","patient_name":"Tan Chay Yee","philhealth_number":"21-210942992-0","diagnosis_code":"N20.9","procedure_code":"36100","total_amount":193.00,"philhealth_benefit":100.00,"balance_due":93.00}',
        1,  # parse tier
    )


@pytest.fixture
def test_image_bytes():
    """Valid PNG image bytes for upload."""
    buf = BytesIO()
    Image.new("RGB", (200, 200), (128, 128, 128)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def client(sample_model_output):
    """FastAPI test client with mocked model and real rule engine.

    Creates a fresh FastAPI app WITHOUT the lifespan (which loads the
    real GPU model). Instead, mocks the model and wires dependencies
    directly.
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from api.core.model import manager
    from api.routes.analyze import router as analyze_router, set_dependencies
    from api.routes.health import router as health_router
    from api.core.rule_engine import RuleEngine
    from api.core.encryption import generate_key, load_key
    from api.core.exceptions import FeeverError
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from datetime import datetime, timezone
    import uuid
    from pathlib import Path

    # Build a test app without lifespan
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(analyze_router)

    @app.exception_handler(FeeverError)
    async def feever_handler(request: Request, exc: FeeverError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "request_id": str(uuid.uuid4()),
                "status_code": exc.status_code,
                "error_type": exc.error_type,
                "detail": exc.detail,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    # Wire dependencies
    engine = RuleEngine(
        db_path="models/reserved/hospital_db.sqlite",
        annex_a_path="models/reserved/philhealth_annex_a.json",
        annex_b_path="models/reserved/philhealth_annex_b.json",
    )
    key = load_key(generate_key())
    set_dependencies(engine, key, Path("data/records"))

    # Mock model
    with patch.object(manager, "_loaded", True), \
         patch.object(manager, "run_inference", return_value=sample_model_output), \
         patch.object(manager, "_flush_cuda"), \
         patch.object(manager, "device", "cpu"):

        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


class TestAnalyzeSuccess:
    def test_valid_request_returns_200(self, client, test_image_bytes):
        resp = client.post(
            "/analyze",
            files={"image": ("test.png", test_image_bytes, "image/png")},
            data={"permission_to_record": "false"},
        )
        assert resp.status_code == 200

    def test_response_has_all_phase4_fields(self, client, test_image_bytes):
        resp = client.post(
            "/analyze",
            files={"image": ("test.png", test_image_bytes, "image/png")},
        )
        body = resp.json()

        # Top-level fields
        assert "request_id" in body
        assert "timestamp" in body
        assert "ocr_result" in body
        assert "rule_engine" in body
        assert "discrepancies" in body
        assert "summary" in body
        assert "extraction_notes" in body
        assert "processing" in body
        assert "recorded" in body

    def test_ocr_result_has_confidence(self, client, test_image_bytes):
        resp = client.post(
            "/analyze",
            files={"image": ("test.png", test_image_bytes, "image/png")},
        )
        ocr = resp.json()["ocr_result"]

        # Each field should have value + confidence
        for field in ["patient_name", "billing_date", "total_amount",
                       "philhealth_number", "diagnosis_code", "procedure_code"]:
            assert "value" in ocr[field], f"{field} missing 'value'"
            assert "confidence" in ocr[field], f"{field} missing 'confidence'"

    def test_philhealth_matches_have_codes(self, client, test_image_bytes):
        resp = client.post(
            "/analyze",
            files={"image": ("test.png", test_image_bytes, "image/png")},
        )
        matches = resp.json()["rule_engine"]["philhealth_matches"]
        assert len(matches) >= 1
        for m in matches:
            assert "matched_code" in m
            assert "matched_description" in m
            assert "match_score" in m
            assert "match_method" in m

    def test_processing_block(self, client, test_image_bytes):
        resp = client.post(
            "/analyze",
            files={"image": ("test.png", test_image_bytes, "image/png")},
        )
        proc = resp.json()["processing"]
        assert proc["parse_tier"] == 1
        assert "stages" in proc
        assert "thresholds_used" in proc
        assert proc["total_ms"] >= 0

    def test_summary_fields_excluded(self, client, test_image_bytes):
        resp = client.post(
            "/analyze",
            files={"image": ("test.png", test_image_bytes, "image/png")},
        )
        body = resp.json()
        line_items = body["ocr_result"]["line_items"]
        summary_items = [li for li in line_items if li["is_summary"]]
        assert len(summary_items) >= 1

        # Rule engine should have no hospital_db_matches for summary items
        # (they were filtered out before being sent)
        notes = body["extraction_notes"]
        assert any("summary fields" in n for n in notes)

    def test_raw_ocr_text_hidden_without_permission(self, client, test_image_bytes):
        resp = client.post(
            "/analyze",
            files={"image": ("test.png", test_image_bytes, "image/png")},
            data={"permission_to_record": "false"},
        )
        assert resp.json()["processing"]["raw_ocr_text"] is None


class TestAnalyzeErrors:
    def test_corrupted_image_returns_structured_error(self, client):
        resp = client.post(
            "/analyze",
            files={"image": ("bad.png", b"not an image", "image/png")},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"] is True
        assert body["error_type"] == "invalid_image"
        assert "request_id" in body
        assert "timestamp" in body

    def test_wrong_content_type(self, client):
        resp = client.post(
            "/analyze",
            files={"image": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"] is True
        assert body["error_type"] == "invalid_image"

    def test_extraction_failure_returns_422(self, client, test_image_bytes):
        """When model output can't be parsed, return 422."""
        from api.core.model import manager
        with patch.object(manager, "run_inference", side_effect=ValueError("parse failed")):
            resp = client.post(
                "/analyze",
                files={"image": ("test.png", test_image_bytes, "image/png")},
            )
        assert resp.status_code == 422
        body = resp.json()
        assert body["error_type"] == "extraction_failed"


class TestAnalyzeConcurrency:
    def test_busy_returns_503(self, client, test_image_bytes):
        """Second concurrent request should get 503."""
        from api.core.model import manager
        # Hold the lock
        manager.lock.acquire()
        try:
            resp = client.post(
                "/analyze",
                files={"image": ("test.png", test_image_bytes, "image/png")},
            )
            assert resp.status_code == 503
            body = resp.json()
            assert body["error_type"] == "busy"
        finally:
            manager.lock.release()
