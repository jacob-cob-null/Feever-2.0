"""POST /analyze — full inference + rule engine pipeline (Phase 4 HITL)."""

import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.core.confidence import assess_confidence
from api.core.encryption import encrypt_and_save
from api.core.model import manager
from api.core.normalizer import InvalidImageError, normalize, validate_image
from api.schemas.response import (
    AnalyzeResponse,
    ConfidenceField,
    Discrepancy,
    LineItem,
    OcrResult,
    ProcessingInfo,
    ProcessingStages,
    RuleEngineResult,
    Summary,
    ThresholdsUsed,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Injected by main.py at startup
_rule_engine = None
_aes_key: bytes | None = None
_records_dir: Path = Path("data/records")

SUMMARY_FIELD_LABELS = {
    "total amount", "philhealth benefit", "balance due",
    "grand total", "subtotal", "sub-total", "amount due",
    "total charges", "net amount",
}


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
    extraction_notes: list[str] = []
    t_start = time.perf_counter()

    logger.info(
        "request_id=%s | stage=received | content_type=%s | size_bytes=%s | permission_to_record=%s",
        request_id, image.content_type, image.size, permission_to_record,
    )

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
        t_norm = time.perf_counter()
        try:
            pil_image = normalize(image_bytes)
        except InvalidImageError as e:
            raise HTTPException(status_code=400, detail=str(e))
        norm_ms = int((time.perf_counter() - t_norm) * 1000)
        logger.info("request_id=%s | stage=normalized | elapsed_ms=%d", request_id, norm_ms)

        # 4. Run inference
        t_infer = time.perf_counter()
        try:
            raw_ocr, raw_text, parse_tier = manager.run_inference(pil_image)
        except ValueError as e:
            # All 3 parse tiers failed
            logger.error(
                "request_id=%s | stage=inference | error=extraction_failed | detail=%s",
                request_id, e,
            )
            raise HTTPException(
                status_code=422,
                detail="Could not extract structured data from document",
            )
        except Exception as e:
            logger.exception("request_id=%s | stage=inference | error=%s", request_id, type(e).__name__)
            raise HTTPException(
                status_code=500,
                detail=f"Inference error: {type(e).__name__}: {e}",
            )
        infer_ms = int((time.perf_counter() - t_infer) * 1000)
        logger.info(
            "request_id=%s | stage=inference_done | elapsed_ms=%d | parse_tier=%d",
            request_id, infer_ms, parse_tier,
        )
    finally:
        # 5 + 6. Flush CUDA and release lock (always)
        manager._flush_cuda()
        manager.lock.release()

    if parse_tier > 1:
        extraction_notes.append(
            f"OCR output required tier-{parse_tier} parsing — review raw_ocr_text for accuracy"
        )

    # 7. Parse OCR output into response schema with confidence
    ocr_result, notes = _build_ocr_result(raw_ocr)
    extraction_notes.extend(notes)

    # 8 + 9 + 10. Rule engine checks
    t_rule = time.perf_counter()
    # Filter out summary fields for rule engine input
    rule_items = [
        {"description": li.description, "price": li.price}
        for li in ocr_result.line_items
        if not li.is_summary
    ]

    if _rule_engine is not None:
        rule_result, discrepancies, summary = _rule_engine.check(
            {
                "hospital_name": ocr_result.hospital_name.value,
                "diagnosis_code": raw_ocr.get("diagnosis_code"),
                "procedure_code": raw_ocr.get("procedure_code"),
                "total_amount": _to_float(ocr_result.total_amount.value),
                "line_items": rule_items,
            }
        )
    else:
        rule_result = RuleEngineResult()
        discrepancies = []
        summary = Summary()

    rule_ms = int((time.perf_counter() - t_rule) * 1000)
    logger.info(
        "request_id=%s | stage=rule_engine | ph_matches=%d | db_matches=%d | discrepancies=%d | elapsed_ms=%d",
        request_id,
        len(rule_result.philhealth_matches),
        len(rule_result.hospital_db_matches),
        len(discrepancies),
        rule_ms,
    )

    # Count summary fields that were excluded
    summary_count = sum(1 for li in ocr_result.line_items if li.is_summary)
    if summary_count > 0:
        extraction_notes.append(
            f"{summary_count} line items were summary fields "
            f"({', '.join(li.description for li in ocr_result.line_items if li.is_summary)}) "
            f"and were excluded from rule engine matching"
        )

    # 11. Encrypt + record if permitted
    enc_ms = None
    recorded = False
    if permission_to_record and _aes_key:
        t_enc = time.perf_counter()
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
            logger.error("request_id=%s | stage=encryption | error=%s", request_id, e)
        enc_ms = int((time.perf_counter() - t_enc) * 1000)

    total_ms = int((time.perf_counter() - t_start) * 1000)
    logger.info(
        "request_id=%s | stage=complete | total_ms=%d | recorded=%s",
        request_id, total_ms, recorded,
    )

    # Build processing info
    processing = ProcessingInfo(
        total_ms=total_ms,
        stages=ProcessingStages(
            normalization_ms=norm_ms,
            inference_ms=infer_ms,
            rule_engine_ms=rule_ms,
            encryption_ms=enc_ms,
        ),
        thresholds_used=ThresholdsUsed(
            hospital_fuzzy=_rule_engine.hospital_threshold if _rule_engine else 80,
            philhealth_fuzzy=_rule_engine.philhealth_threshold if _rule_engine else 82,
            price_delta_tolerance=_rule_engine.price_tolerance if _rule_engine else 0.05,
        ),
        parse_tier=parse_tier,
        raw_ocr_text=raw_text if permission_to_record else None,
    )

    # 12. Return response
    return AnalyzeResponse(
        request_id=request_id,
        timestamp=timestamp,
        ocr_result=ocr_result,
        rule_engine=rule_result,
        discrepancies=discrepancies,
        summary=summary,
        extraction_notes=extraction_notes,
        processing=processing,
        recorded=recorded,
    )


def _build_ocr_result(raw: dict) -> tuple[OcrResult, list[str]]:
    """Map raw model output (8-field schema) to OcrResult with confidence.

    Returns:
        (ocr_result, extraction_notes)
    """
    notes: list[str] = []

    def _cf(field: str, value) -> ConfidenceField:
        return ConfidenceField(
            value=value,
            confidence=assess_confidence(field, value),
        )

    # Build confidence-wrapped fields
    hospital_name = _cf("hospital_name", raw.get("hospital_name"))
    patient_name = _cf("patient_name", raw.get("patient_name"))
    billing_date = _cf("date", raw.get("date"))
    total_amount = _cf("total_amount", raw.get("total_amount"))
    tax_amount = _cf("tax_amount", raw.get("tax_amount"))
    philhealth_number = _cf("philhealth_number", raw.get("philhealth_number"))
    diagnosis_code = _cf("diagnosis_code", raw.get("diagnosis_code"))
    procedure_code = _cf("procedure_code", raw.get("procedure_code"))
    philhealth_benefit = _cf("philhealth_benefit", raw.get("philhealth_benefit"))
    balance_due = _cf("balance_due", raw.get("balance_due"))

    # Extraction notes for missing fields that affect downstream processing
    if hospital_name.value is None:
        notes.append(
            "hospital_name was not found in the document — "
            "rule engine searched all hospitals instead of filtering"
        )
    if diagnosis_code.value is None:
        notes.append(
            "diagnosis_code was not extracted — PhilHealth Annex A code matching was skipped"
        )
    if procedure_code.value is None:
        notes.append(
            "procedure_code was not extracted — PhilHealth Annex B code matching was skipped"
        )

    # Build line items — tag summary fields
    line_items = []
    summary_fields = [
        ("Total Amount", raw.get("total_amount")),
        ("PhilHealth Benefit", raw.get("philhealth_benefit")),
        ("Balance Due", raw.get("balance_due")),
    ]
    for desc, val in summary_fields:
        if val is not None:
            is_summary = desc.lower() in SUMMARY_FIELD_LABELS
            line_items.append(
                LineItem(
                    description=desc,
                    quantity=1,
                    price=_to_float(val),
                    is_summary=is_summary,
                )
            )

    return (
        OcrResult(
            hospital_name=hospital_name,
            patient_name=patient_name,
            billing_date=billing_date,
            total_amount=total_amount,
            tax_amount=tax_amount,
            philhealth_number=philhealth_number,
            diagnosis_code=diagnosis_code,
            procedure_code=procedure_code,
            philhealth_benefit=philhealth_benefit,
            balance_due=balance_due,
            line_items=line_items,
        ),
        notes,
    )


def _to_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
