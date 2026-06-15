"""Pydantic response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- OCR result ---

class LineItem(BaseModel):
    description: str
    quantity: int | None = None
    price: float | None = None


class OcrResult(BaseModel):
    hospital_name: str | None = None
    patient_name: str | None = None
    billing_date: str | None = None
    total_amount: float | None = None
    tax_amount: float | None = None
    line_items: list[LineItem] = Field(default_factory=list)


# --- Rule engine ---

class PhilhealthMatch(BaseModel):
    item: str
    claimed_amount: float
    annex_source: str  # "A" | "B"
    case_rate_ceiling: float
    hospital_share: float
    professional_fee: float
    status: str  # WITHIN_LIMIT | EXCEEDS_LIMIT | NOT_COVERED


class HospitalDbMatch(BaseModel):
    item: str
    claimed_amount: float
    reference_price: float
    matched_hospital: str
    delta_percent: float
    status: str  # MATCH | DISCREPANCY | NOT_FOUND


class RuleEngineResult(BaseModel):
    philhealth_matches: list[PhilhealthMatch] = Field(default_factory=list)
    hospital_db_matches: list[HospitalDbMatch] = Field(default_factory=list)


# --- Discrepancies ---

class Discrepancy(BaseModel):
    item: str
    claimed_amount: float
    violation: str
    detail: str
    severity: str  # HIGH | MEDIUM | LOW


# --- Summary ---

class Summary(BaseModel):
    total_items: int = 0
    items_matched: int = 0
    items_flagged: int = 0
    total_claimed: float = 0.0
    total_allowable: float = 0.0
    excess_amount: float = 0.0


# --- Top-level response ---

class AnalyzeResponse(BaseModel):
    request_id: str
    timestamp: str
    ocr_result: OcrResult
    rule_engine: RuleEngineResult
    discrepancies: list[Discrepancy] = Field(default_factory=list)
    summary: Summary
    recorded: bool = False


# --- Health ---

class SubsystemStatus(BaseModel):
    status: str
    device: str | None = None
    vram_used_mb: int | None = None
    vram_total_mb: int | None = None
    record_count: int | None = None
    annex_a_rules: int | None = None
    annex_b_rules: int | None = None
    algorithm: str | None = None


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    uptime_seconds: int
    subsystems: dict[str, SubsystemStatus]
    version: str = "1.0.0"
