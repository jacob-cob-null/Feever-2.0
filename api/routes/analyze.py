"""POST /analyze — full inference + rule engine pipeline."""

import logging
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.core.encryption import encrypt_and_save
from api.core.model import manager
from api.core.normalizer import normalize, validate_image
from api.schemas.response import (
    AnalyzeResponse,
    Discrepancy,
    LineItem,
    OcrResult,
    RuleEngineResult,
    Summary,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Injected by main.py at startup
_rule_engine = None
_aes_key: bytes | None = None
_records_dir: Path = Path("data/records")


def set_dependencies(rule_engine, aes_key: bytes, records_dir: Path) -> None:
    global _rule_engine, _aes_key, _records_dir
    _rule_engine = rule_engine
    _aes_key = aes_key
    _records_dir = records_dir


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    image: UploadFile = File(...),
    permission_to_record: bool = Form(False),
) -> AnalyzeResponse:
    request_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    # 1. Validate request
    image_bytes = await image.read()
    error = validate_image(image.content_type, len(image_bytes))
    if error:
        raise HTTPException(status_code=400, detail=error)

    # 2. Acquire inference lock
    acquired = manager.lock.acquire(blocking=False)
    if not acquired:
        raise HTTPException(
            status_code=503,
            detail="Inference engine busy. Try again shortly.",
        )

    try:
        # 3. Normalize image
        pil_image = normalize(image_bytes)

        # 4. Run inference
        try:
            raw_ocr = manager.run_inference(pil_image)
        except Exception as e:
            logger.error("Inference failed: %s", e)
            raise HTTPException(status_code=500, detail=f"Inference error: {e}")
    finally:
        # 5 + 6. Flush CUDA and release lock (always)
        manager._flush_cuda()
        manager.lock.release()

    # 7. Parse OCR output into response schema
    ocr_result = _build_ocr_result(raw_ocr)

    # 8 + 9 + 10. Rule engine checks
    if _rule_engine is not None:
        rule_result, discrepancies, summary = _rule_engine.check(
            {
                "hospital_name": ocr_result.hospital_name,
                "diagnosis_code": raw_ocr.get("diagnosis_code"),
                "procedure_code": raw_ocr.get("procedure_code"),
                "total_amount": ocr_result.total_amount,
                "line_items": [
                    {"description": li.description, "price": li.price}
                    for li in ocr_result.line_items
                ],
            }
        )
    else:
        rule_result = RuleEngineResult()
        discrepancies = []
        summary = Summary()

    # 11. Encrypt + record if permitted
    recorded = False
    if permission_to_record and _aes_key:
        try:
            response_payload = {
                "request_id": request_id,
                "timestamp": timestamp,
                "ocr_result": ocr_result.model_dump(),
                "discrepancies": [d.model_dump() for d in discrepancies],
            }
            encrypt_and_save(
                payload=response_payload,
                image_bytes=image_bytes,
                key=_aes_key,
                out_dir=_records_dir,
                request_id=request_id,
            )
            recorded = True
        except Exception as e:
            logger.error("Encryption/save failed: %s", e)

    # 12. Return response
    return AnalyzeResponse(
        request_id=request_id,
        timestamp=timestamp,
        ocr_result=ocr_result,
        rule_engine=rule_result,
        discrepancies=discrepancies,
        summary=summary,
        recorded=recorded,
    )


def _build_ocr_result(raw: dict) -> OcrResult:
    """Map raw model output (8-field schema) to OcrResult."""
    # The model outputs: date, patient_name, philhealth_number,
    # diagnosis_code, procedure_code, total_amount, philhealth_benefit,
    # balance_due. Map to our response schema.
    line_items = []

    # Build line items from available fields
    if raw.get("total_amount") is not None:
        line_items.append(
            LineItem(
                description="Total Amount",
                quantity=1,
                price=_to_float(raw.get("total_amount")),
            )
        )
    if raw.get("philhealth_benefit") is not None:
        line_items.append(
            LineItem(
                description="PhilHealth Benefit",
                quantity=1,
                price=_to_float(raw.get("philhealth_benefit")),
            )
        )
    if raw.get("balance_due") is not None:
        line_items.append(
            LineItem(
                description="Balance Due",
                quantity=1,
                price=_to_float(raw.get("balance_due")),
            )
        )

    return OcrResult(
        hospital_name=raw.get("hospital_name"),
        patient_name=raw.get("patient_name"),
        billing_date=raw.get("date"),
        total_amount=_to_float(raw.get("total_amount")),
        tax_amount=None,
        line_items=line_items,
    )


def _to_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
