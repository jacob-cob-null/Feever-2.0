// Types matching backend Pydantic schemas exactly (api/schemas/response.py)

export interface ConfidenceField {
  value: string | number | null;
  confidence: 'high' | 'medium' | 'low' | null;
}

export interface LineItem {
  description: string;
  quantity: number | null;
  price: number | null;
  is_summary: boolean;
}

export interface OcrResult {
  hospital_name: ConfidenceField;
  patient_name: ConfidenceField;
  billing_date: ConfidenceField;
  total_amount: ConfidenceField;
  tax_amount: ConfidenceField;
  philhealth_number: ConfidenceField;
  diagnosis_code: ConfidenceField;
  procedure_code: ConfidenceField;
  philhealth_benefit: ConfidenceField;
  balance_due: ConfidenceField;
  line_items: LineItem[];
}

export type PhilhealthStatus = 'WITHIN_LIMIT' | 'EXCEEDS_LIMIT' | 'NOT_COVERED';

export interface PhilhealthMatch {
  item: string;
  claimed_amount: number;
  annex_source: 'A' | 'B' | 'N/A';
  matched_code: string | null;
  matched_description: string | null;
  case_rate_ceiling: number;
  hospital_share: number;
  professional_fee: number;
  status: PhilhealthStatus;
  match_score: number | null;
  match_method: 'exact_code' | 'fuzzy';
}

export type HospitalDbStatus = 'MATCH' | 'DISCREPANCY' | 'NOT_FOUND';

export interface HospitalDbMatch {
  item: string;
  claimed_amount: number;
  reference_price: number;
  matched_hospital: string;
  matched_service_id: number | null;
  matched_description: string | null;
  delta_percent: number;
  status: HospitalDbStatus;
  match_score: number | null;
  match_method: 'fuzzy';
}

export interface RuleEngineResult {
  philhealth_matches: PhilhealthMatch[];
  hospital_db_matches: HospitalDbMatch[];
}

export type Severity = 'HIGH' | 'MEDIUM' | 'LOW';

export type ViolationType =
  | 'EXCEEDS_PHILHEALTH_CEILING'
  | 'PRICE_MISMATCH'
  | 'NOT_IN_HOSPITAL_SCHEDULE'
  | 'NOT_COVERED';

export interface Discrepancy {
  item: string;
  claimed_amount: number;
  violation: ViolationType;
  detail: string;
  severity: Severity;
  reference_code: string | null;
  reference_source: string | null;
  reviewer_action: string | null;
}

export interface Summary {
  total_items: number;
  items_matched: number;
  items_flagged: number;
  total_claimed: number;
  total_allowable: number;
  excess_amount: number;
}

export interface ProcessingStages {
  normalization_ms: number;
  inference_ms: number;
  rule_engine_ms: number;
  encryption_ms: number | null;
}

export interface ThresholdsUsed {
  hospital_fuzzy: number;
  philhealth_fuzzy: number;
  price_delta_tolerance: number;
}

export interface ProcessingInfo {
  total_ms: number;
  stages: ProcessingStages;
  thresholds_used: ThresholdsUsed;
  parse_tier: 1 | 2 | 3;
  model_version: string;
  raw_ocr_text: string | null;
}

export interface AnalyzeResponse {
  request_id: string;
  timestamp: string;
  ocr_result: OcrResult;
  rule_engine: RuleEngineResult;
  discrepancies: Discrepancy[];
  summary: Summary;
  extraction_notes: string[];
  processing: ProcessingInfo;
  recorded: boolean;
}

export interface SubsystemStatus {
  status: string;
  device?: string;
  vram_used_mb?: number;
  vram_total_mb?: number;
  record_count?: number;
  annex_a_rules?: number;
  annex_b_rules?: number;
  algorithm?: string;
}

export interface HealthResponse {
  status: 'ok' | 'degraded';
  timestamp: string;
  uptime_seconds: number;
  subsystems: {
    model: SubsystemStatus;
    hospital_db: SubsystemStatus;
    philhealth_annex: SubsystemStatus;
    encryption: SubsystemStatus;
    inference_lock: SubsystemStatus;
  };
  version: string;
}

export interface ApiError {
  error: true;
  request_id: string | null;
  status_code: number;
  error_type: string;
  detail: string;
  timestamp: string;
}

// Workflow state machine
export type WorkflowState =
  | { phase: 'idle' }
  | { phase: 'processing'; file: File; startedAt: number }
  | { phase: 'results'; file: File; data: AnalyzeResponse }
  | { phase: 'error'; file: File | null; error: ApiError };

export type WorkflowAction =
  | { type: 'START_UPLOAD'; file: File }
  | { type: 'UPLOAD_SUCCESS'; data: AnalyzeResponse }
  | { type: 'UPLOAD_ERROR'; error: ApiError }
  | { type: 'RESET' };
