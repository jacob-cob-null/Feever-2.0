"""Pydantic response models — Phase 4 (Human-in-the-Loop)."""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- Confidence wrapper ---

class ConfidenceField(BaseModel):
    """A value paired with a confidence indicator for human review."""
    value: str | float | None = None
    confidence: str | None = None  # "high" | "medium" | "low" | null


# --- OCR result ---

class LineItem(BaseModel):
    description: str
    quantity: int | None = None
    price: float | None = None
    is_summary: bool = False


class OcrResult(BaseModel):
    hospital_name: ConfidenceField = Field(default_factory=ConfidenceField)
    patient_name: ConfidenceField = Field(default_factory=ConfidenceField)
    billing_date: ConfidenceField = Field(default_factory=ConfidenceField)
    total_amount: ConfidenceField = Field(default_factory=ConfidenceField)
    tax_amount: ConfidenceField = Field(default_factory=ConfidenceField)
    philhealth_number: ConfidenceField = Field(default_factory=ConfidenceField)
    diagnosis_code: ConfidenceField = Field(default_factory=ConfidenceField)
    procedure_code: ConfidenceField = Field(default_factory=ConfidenceField)
    philhealth_benefit: ConfidenceField = Field(default_factory=ConfidenceField)
    balance_due: ConfidenceField = Field(default_factory=ConfidenceField)
    line_items: list[LineItem] = Field(default_factory=list)


# --- Rule engine ---

class PhilhealthMatch(BaseModel):
    item: str
    claimed_amount: float
    annex_source: str  # "A" | "B" | "N/A"
    matched_code: str | None = None  # ICD-10 or RVS code from annex
    matched_description: str | None = None  # official annex description
    case_rate_ceiling: float = 0
    hospital_share: float = 0
    professional_fee: float = 0
    status: str  # WITHIN_LIMIT | EXCEEDS_LIMIT | NOT_COVERED
    match_score: float | None = None  # 0-100 fuzzy score
    match_method: str | None = None  # "exact_code" | "fuzzy"


class HospitalDbMatch(BaseModel):
    item: str
    claimed_amount: float
    reference_price: float = 0
    matched_hospital: str = ""
    matched_service_id: int | None = None  # service_ID primary key
    matched_description: str | None = None  # official service name from DB
    delta_percent: float = 0
    status: str  # MATCH | DISCREPANCY | NOT_FOUND
    match_score: float | None = None  # 0-100 fuzzy score
    match_method: str | None = None  # "fuzzy"


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
    reference_code: str | None = None  # e.g. "ICD:I10", "RVS:90.5.0.10", "service_ID:1247"
    reference_source: str | None = None  # e.g. "philhealth_annex_a", "hospital_db:Ospital ng Angeles"
    reviewer_action: str | None = None


# --- Summary ---

class Summary(BaseModel):
    total_items: int = 0
    items_matched: int = 0
    items_flagged: int = 0
    total_claimed: float = 0.0
    total_allowable: float = 0.0
    excess_amount: float = 0.0


# --- Processing info ---

class ProcessingStages(BaseModel):
    normalization_ms: int = 0
    inference_ms: int = 0
    rule_engine_ms: int = 0
    encryption_ms: int | None = None


class ThresholdsUsed(BaseModel):
    hospital_fuzzy: float = 80
    philhealth_fuzzy: float = 82
    price_delta_tolerance: float = 0.05


class ProcessingInfo(BaseModel):
    total_ms: int = 0
    stages: ProcessingStages = Field(default_factory=ProcessingStages)
    thresholds_used: ThresholdsUsed = Field(default_factory=ThresholdsUsed)
    parse_tier: int = 1  # 1 = clean, 2 = repaired, 3 = partial
    model_version: str = "qwen3vl-4b-feever-v1"
    raw_ocr_text: str | None = None  # only when permission_to_record=true


# --- Top-level response ---

class AnalyzeResponse(BaseModel):
    request_id: str
    timestamp: str
    ocr_result: OcrResult
    rule_engine: RuleEngineResult
    discrepancies: list[Discrepancy] = Field(default_factory=list)
    summary: Summary
    extraction_notes: list[str] = Field(default_factory=list)
    processing: ProcessingInfo = Field(default_factory=ProcessingInfo)
    recorded: bool = False


# --- Structured error response ---

class ErrorResponse(BaseModel):
    error: bool = True
    request_id: str | None = None
    status_code: int
    error_type: str
    detail: str
    timestamp: str


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
