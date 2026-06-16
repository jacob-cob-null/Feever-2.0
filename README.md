# Fee-Ver 2.0

Medical billing document analysis API powered by a fine-tuned Qwen3-VL-4B vision-language model. Accepts a hospital invoice image, extracts structured data via OCR, cross-references against a Philippine hospital services database (3,017 records) and PhilHealth case rate rules (8,923 Annex A+B entries), and returns a detailed discrepancy report designed for human-in-the-loop review.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Frontend (your app)                            │
│  Upload image → POST /analyze → Display structured results              │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ multipart/form-data
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend (8000)                           │
│                                                                         │
│  ┌───────────┐   ┌──────────────┐   ┌──────────────┐   ┌───────────┐  │
│  │ Normalizer │──▶│  Qwen3-VL-4B │──▶│ Rule Engine  │──▶│ Encryptor │  │
│  │ 1024×1024  │   │  4-bit BnB   │   │ PhilHealth + │   │ AES-256   │  │
│  │ letterbox  │   │  LoRA merged │   │ Hospital DB  │   │ GCM       │  │
│  └───────────┘   └──────────────┘   └──────────────┘   └───────────┘  │
│                                                                         │
│  Reference Data:                                                        │
│  • hospital_db.sqlite — 3,017 medical service records (3 hospitals)     │
│  • philhealth_annex_a.json — 4,610 ICD-10 medical case rates            │
│  • philhealth_annex_b.json — 4,313 RVS procedure case rates             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## API Reference

### `GET /health`

Returns subsystem statuses. Use this to check if the backend is ready before enabling the upload button.

**Response:**

```json
{
  "status": "ok",
  "timestamp": "2026-06-16T11:00:00Z",
  "uptime_seconds": 105,
  "subsystems": {
    "model": { "status": "loaded", "device": "cuda:0", "vram_used_mb": 2800, "vram_total_mb": 12288 },
    "hospital_db": { "status": "ok", "record_count": 3017 },
    "philhealth_annex": { "status": "ok", "annex_a_rules": 4610, "annex_b_rules": 4313 },
    "encryption": { "status": "ok", "algorithm": "AES-256-GCM" },
    "inference_lock": { "status": "free" }
  },
  "version": "1.0.0"
}
```

**Key fields:**

| Field | Values |
|-------|--------|
| `status` | `"ok"` = all systems go. `"degraded"` = check subsystems for details. |
| `subsystems.model.status` | `"loaded"` or `"error"` |
| `subsystems.inference_lock.status` | `"free"` or `"held"` (held = currently processing another image) |

---

### `POST /analyze`

The core endpoint. Accepts an invoice image, returns full extraction + rule engine analysis.

**Request** — `multipart/form-data`:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image` | file | Yes | JPG, PNG, or WebP. Max 10 MB. |
| `permission_to_record` | string | No (default: `"false"`) | Set to `"true"` to encrypt and save the request to `data/records/`. When true, `raw_ocr_text` is included in the response. |

**Example request (JavaScript):**

```javascript
const formData = new FormData();
formData.append('image', fileInput.files[0]);
formData.append('permission_to_record', 'false');

const response = await fetch('http://localhost:8000/analyze', {
  method: 'POST',
  body: formData,
});
const result = await response.json();
```

**Example request (Python):**

```python
import httpx

with open("invoice.png", "rb") as f:
    resp = httpx.post(
        "http://localhost:8000/analyze",
        files={"image": ("invoice.png", f, "image/png")},
        data={"permission_to_record": "false"},
    )
result = resp.json()
```

---

### Full Response Schema

Every successful response (`200 OK`) has this exact shape:

```json
{
  "request_id": "032ebfc5-5fde-47d4-beef-8d2e6d11f6c2",
  "timestamp": "2026-06-16T11:06:32.221125+00:00",

  "ocr_result": {
    "hospital_name":      { "value": "Dr Andres M Luciano District Hospital", "confidence": "high" },
    "patient_name":       { "value": "Tammy Williams", "confidence": "high" },
    "billing_date":       { "value": "2026-03-24", "confidence": "high" },
    "total_amount":       { "value": 19519.22, "confidence": "high" },
    "tax_amount":         { "value": null, "confidence": null },
    "philhealth_number":  { "value": null, "confidence": null },
    "diagnosis_code":     { "value": null, "confidence": null },
    "procedure_code":     { "value": null, "confidence": null },
    "philhealth_benefit": { "value": null, "confidence": null },
    "balance_due":        { "value": null, "confidence": null },
    "line_items": [
      { "description": "PELVIS CROSS-TABLE (RIGHT)", "quantity": 1, "price": 100.0, "is_summary": false },
      { "description": "MULTIVITAMINS; 100 TABS/BOX (DONATION)", "quantity": 1, "price": 1.64, "is_summary": false },
      { "description": "Total Amount", "quantity": 1, "price": 19519.22, "is_summary": true }
    ]
  },

  "rule_engine": {
    "philhealth_matches": [
      {
        "item": "PELVIS CROSS-TABLE (RIGHT)",
        "claimed_amount": 100.0,
        "annex_source": "N/A",
        "matched_code": null,
        "matched_description": null,
        "case_rate_ceiling": 0,
        "hospital_share": 0,
        "professional_fee": 0,
        "status": "NOT_COVERED",
        "match_score": 54.2,
        "match_method": "fuzzy"
      }
    ],
    "hospital_db_matches": [
      {
        "item": "PELVIS CROSS-TABLE (RIGHT)",
        "claimed_amount": 100.0,
        "reference_price": 100.0,
        "matched_hospital": "Dr. Andres M. Luciano District Hospital",
        "matched_service_id": 630,
        "matched_description": "PELVIS CROSS-TABLE (RIGHT)",
        "delta_percent": 0,
        "status": "MATCH",
        "match_score": 100,
        "match_method": "fuzzy"
      }
    ]
  },

  "discrepancies": [
    {
      "item": "PELVIS CROSS-TABLE (RIGHT)",
      "claimed_amount": 100.0,
      "violation": "NOT_COVERED",
      "detail": "'PELVIS CROSS-TABLE (RIGHT)' not found in PhilHealth Annex A or B",
      "severity": "LOW",
      "reference_code": null,
      "reference_source": null,
      "reviewer_action": "'PELVIS CROSS-TABLE (RIGHT)' did not match any PhilHealth case rate code (best fuzzy score: 54/100). Check if a different service description or code applies."
    }
  ],

  "summary": {
    "total_items": 10,
    "items_matched": 10,
    "items_flagged": 10,
    "total_claimed": 18604.49,
    "total_allowable": 18604.49,
    "excess_amount": 0
  },

  "extraction_notes": [
    "Date normalized: 'MAR 24, 2026' → '2026-03-24'",
    "Cross-validation: line items sum (18604.49) does not match total_amount (19519.22) — review for missing items",
    "diagnosis_code was not extracted — PhilHealth Annex A code matching was skipped",
    "1 line items were summary fields (Total Amount) and were excluded from rule engine matching"
  ],

  "processing": {
    "total_ms": 67938,
    "stages": {
      "normalization_ms": 79,
      "inference_ms": 67412,
      "rule_engine_ms": 437,
      "encryption_ms": null
    },
    "thresholds_used": {
      "hospital_fuzzy": 80,
      "philhealth_fuzzy": 82,
      "price_delta_tolerance": 0.05
    },
    "parse_tier": 1,
    "model_version": "qwen3vl-4b-feever-v1",
    "raw_ocr_text": null
  },

  "recorded": false
}
```

---

### Response Field Reference

#### `ocr_result` — Extracted document fields

Each field (except `line_items`) is a `ConfidenceField` object:

```typescript
interface ConfidenceField {
  value: string | number | null;
  confidence: "high" | "medium" | "low" | null;
}
```

| Confidence | Meaning |
|------------|---------|
| `"high"` | Field present, parsed cleanly, passes format validation |
| `"medium"` | Field present but ambiguous (e.g. non-ISO date, single-word name) |
| `"low"` | Field present but suspicious (e.g. future date, negative amount) |
| `null` | Field not found in document |

**OCR fields:**

| Field | Type | Notes |
|-------|------|-------|
| `hospital_name` | string \| null | Hospital/clinic name, usually from document header |
| `patient_name` | string \| null | Full patient name |
| `billing_date` | string \| null | Auto-normalized to ISO `YYYY-MM-DD` when possible |
| `total_amount` | number \| null | Total billed amount |
| `tax_amount` | number \| null | Tax amount (rare in Philippine billing) |
| `philhealth_number` | string \| null | 12-digit PhilHealth member ID (may have dashes) |
| `diagnosis_code` | string \| null | ICD-10 code (e.g. `"N20.9"`, `"I10"`) |
| `procedure_code` | string \| null | RVS procedure code (e.g. `"36100"`, `"90.5.0.10"`) |
| `philhealth_benefit` | number \| null | PhilHealth coverage amount |
| `balance_due` | number \| null | Remaining balance after PhilHealth |

**`line_items`** — Array of itemized charges extracted from the billing table:

```typescript
interface LineItem {
  description: string;    // Service/item name
  quantity: number | null; // Usually 1
  price: number | null;    // Amount charged
  is_summary: boolean;     // true = summary field (Total Amount, etc.), excluded from rule engine
}
```

Items with `is_summary: true` were excluded from rule engine matching to prevent false positives.

#### `rule_engine` — Cross-reference results

**`philhealth_matches`** — Each non-summary line item is fuzzy-matched against PhilHealth Annex A (ICD-10 medical codes) and Annex B (RVS procedure codes):

| Field | Type | Notes |
|-------|------|-------|
| `item` | string | The line item description that was checked |
| `claimed_amount` | number | Price on the invoice |
| `annex_source` | `"A"` \| `"B"` \| `"N/A"` | Which annex matched. `"N/A"` = no match found |
| `matched_code` | string \| null | The ICD-10 or RVS code that matched |
| `matched_description` | string \| null | Official annex description |
| `case_rate_ceiling` | number | PhilHealth maximum allowable amount |
| `hospital_share` | number | Hospital's portion of the case rate |
| `professional_fee` | number | Doctor's portion of the case rate |
| `status` | string | See status table below |
| `match_score` | number | 0-100 fuzzy match score |
| `match_method` | `"exact_code"` \| `"fuzzy"` | How the match was found |

**PhilHealth status values:**

| Status | Meaning |
|--------|---------|
| `WITHIN_LIMIT` | Claimed amount is within the PhilHealth ceiling |
| `EXCEEDS_LIMIT` | Claimed amount exceeds the PhilHealth ceiling |
| `NOT_COVERED` | Item does not match any PhilHealth case rate |

**`hospital_db_matches`** — Each non-summary line item is fuzzy-matched against the hospital services database (3,017 records across 3 hospitals):

| Field | Type | Notes |
|-------|------|-------|
| `item` | string | The line item description |
| `claimed_amount` | number | Price on the invoice |
| `reference_price` | number | Price in the hospital database |
| `matched_hospital` | string | Which hospital's record matched |
| `matched_service_id` | number \| null | Primary key in hospital DB |
| `matched_description` | string \| null | Official service name from DB |
| `delta_percent` | number | Price difference as percentage |
| `status` | string | See status table below |
| `match_score` | number | 0-100 fuzzy match score |
| `match_method` | `"fuzzy"` | Always fuzzy for hospital DB |

**Hospital DB status values:**

| Status | Meaning |
|--------|---------|
| `MATCH` | Item found, price within tolerance (default 5%) |
| `DISCREPANCY` | Item found, price differs beyond tolerance |
| `NOT_FOUND` | Item not in hospital database |

#### `discrepancies` — Flagged issues for reviewer

Only populated when something is wrong. Each discrepancy includes actionable guidance:

| Field | Type | Notes |
|-------|------|-------|
| `item` | string | Which line item or code triggered the flag |
| `claimed_amount` | number | Amount on the invoice |
| `violation` | string | Machine-readable violation type (see below) |
| `detail` | string | Human-readable description of the issue |
| `severity` | `"HIGH"` \| `"MEDIUM"` \| `"LOW"` | Urgency level |
| `reference_code` | string \| null | e.g. `"ICD:N20.9"`, `"service_ID:1247"` |
| `reference_source` | string \| null | e.g. `"philhealth_annex_a"`, `"hospital_db:Ospital ng Angeles"` |
| `reviewer_action` | string | What the human reviewer should do |

**Violation types:**

| Violation | Severity | What happened |
|-----------|----------|---------------|
| `EXCEEDS_PHILHEALTH_CEILING` | HIGH | Claimed amount exceeds PhilHealth case rate ceiling |
| `PRICE_MISMATCH` | MEDIUM | Price differs from hospital DB reference price by > 5% |
| `NOT_IN_HOSPITAL_SCHEDULE` | MEDIUM | Item not found in any hospital's service schedule |
| `NOT_COVERED` | LOW | Item not found in PhilHealth Annex A or B |

#### `summary` — Aggregate counts

| Field | Type | Notes |
|-------|------|-------|
| `total_items` | number | Number of non-summary line items checked |
| `items_matched` | number | Items that matched in hospital DB |
| `items_flagged` | number | Items with at least one discrepancy |
| `total_claimed` | number | Sum of all non-summary line item prices |
| `total_allowable` | number | Sum of reference prices for matched items |
| `excess_amount` | number | `total_claimed - total_allowable` (0 if no excess) |

#### `extraction_notes` — System transparency

Array of strings explaining what the system did or couldn't do during processing.

Common notes:

| Note pattern | Meaning |
|-------------|---------|
| `"Date normalized: 'MAR 24, 2026' → '2026-03-24'"` | Date was converted to ISO format |
| `"Cross-validation: line items sum (...) does not match total_amount (...)"` | Model may have missed some line items |
| `"hospital_name was not found..."` | Hospital name wasn't extracted |
| `"diagnosis_code was not extracted..."` | PhilHealth code matching was skipped |
| `"N line items were summary fields..."` | Summary items were excluded from rule engine |
| `"OCR output required tier-N parsing..."` | Model output wasn't clean JSON (lower confidence) |

#### `processing` — Timing and metadata

| Field | Type | Notes |
|-------|------|-------|
| `total_ms` | number | Total request processing time in milliseconds |
| `stages.normalization_ms` | number | Image preprocessing time |
| `stages.inference_ms` | number | Model inference time (dominant cost) |
| `stages.rule_engine_ms` | number | Cross-reference checking time |
| `stages.encryption_ms` | number \| null | Encryption time (null if not recorded) |
| `thresholds_used.hospital_fuzzy` | number | Fuzzy match threshold for hospital DB (0-100) |
| `thresholds_used.philhealth_fuzzy` | number | Fuzzy match threshold for PhilHealth (0-100) |
| `thresholds_used.price_delta_tolerance` | number | Price difference tolerance (0.05 = 5%) |
| `parse_tier` | 1 \| 2 \| 3 | JSON parsing quality (1=clean, 2=repaired, 3=partial) |
| `model_version` | string | Model identifier |
| `raw_ocr_text` | string \| null | Raw model output (only when `permission_to_record=true`) |

---

### Error Responses

All errors return this consistent shape (never raw stack traces):

```json
{
  "error": true,
  "request_id": "abc-123",
  "status_code": 400,
  "error_type": "invalid_image",
  "detail": "Unsupported image type: application/pdf. Use JPG, PNG, or WebP.",
  "timestamp": "2026-06-16T11:00:00Z"
}
```

**Error types:**

| HTTP Code | `error_type` | Meaning |
|-----------|-------------|---------|
| 400 | `invalid_image` | Bad file type or exceeds 10 MB. `detail` is user-safe. |
| 422 | `extraction_failed` | Model couldn't extract structured data from the image. |
| 503 | `busy` | Another image is currently being processed (inference lock held). |
| 503 | `not_ready` | Server is still loading the model on startup. |
| 504 | `inference_timeout` | Inference exceeded the timeout budget. |
| 500 | `internal_error` | Unexpected server error. `detail` may contain internal info. |

---

### CORS

The backend allows all origins (`*`). No CORS configuration needed on the frontend.

---

### Important Behavior Notes

| Behavior | Detail |
|----------|--------|
| **Sequential processing** | The backend processes one image at a time (inference lock). Concurrent requests get `503 busy`. |
| **Inference time** | ~60-70s on RTX 3060, ~15-20s on datacenter GPUs (A10G, L4). |
| **Thinking mode** | The model uses Qwen3's internal reasoning (generates a think block before the JSON). This is not configurable — it's how the model was fine-tuned. |
| **Line items** | The model extracts itemized charges from billing tables. Documents without tables will have only summary items (`is_summary: true`). |
| **Date normalization** | Dates are auto-converted to ISO `YYYY-MM-DD` when possible. The original format is noted in `extraction_notes`. |
| **Summary field filtering** | Items like "Total Amount", "PhilHealth Benefit", "Balance Due" are tagged `is_summary: true` and excluded from rule engine matching. |
| **PhilHealth matching** | Line items are fuzzy-matched against Annex A (medical) and Annex B (procedure) codes. Items below the fuzzy threshold (82/100) get `NOT_COVERED`. This is expected for medications and supplies — PhilHealth annexes cover diagnoses and procedures, not individual drugs. |
| **Privacy** | When `permission_to_record=false`, no data is persisted and `raw_ocr_text` is null. Compliant with RA 10173 (Philippine Data Privacy Act). |

---

## Running the Backend

### Prerequisites

| Requirement | How to check | Install |
|-------------|-------------|---------|
| **Python 3.11** (not 3.12+) | `python --version` | [python.org](https://www.python.org/downloads/release/python-3119/) |
| **NVIDIA GPU driver >= 550** | `nvidia-smi` | [nvidia.com/drivers](https://www.nvidia.com/Download/index.aspx) |
| **Git LFS** | `git lfs version` | `git lfs install` (one-time) |

### Supported GPUs

| GPU | VRAM | ~Inference Time |
|-----|------|-----------------|
| RTX 3060 12GB | 12 GB | ~65s |
| RTX 4090 | 24 GB | ~20s |
| A10G (AWS) | 24 GB | ~15s |
| L4 (GCP) | 24 GB | ~18s |

**Minimum 8 GB VRAM.** Runtime footprint: ~4.3 GB.

### Setup

```powershell
# 1. Clone and pull model weights
git clone https://github.com/jacob-cob-null/Feever-2.0.git
cd Feever-2.0
git lfs pull

# 2. Create Python 3.11 venv
& "C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python311\python.exe" -m venv .venv311
.\.venv311\Scripts\Activate.ps1

# 3. Install PyTorch with CUDA (one-time, ~2.5 GB download)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124 --timeout 600

# 4. Install dependencies
pip install -r requirements.txt

# 5. Build reference data (one-time, ~30s)
python scripts/build_db.py
python scripts/parse_philhealth.py
python scripts/merge_adapters.py

# 6. Configure environment
cp .env.example .env
python -c "from api.core.encryption import generate_key; print(generate_key())"
# Paste output as AES_SECRET_KEY in .env

# 7. Start server
.\run.ps1
```

Startup takes ~50-90 seconds (downloads base model on first run, then loads from cache).

### Docker

```bash
docker compose up --build
```

Model weights are volume-mounted (not baked into the image). Requires NVIDIA Container Toolkit for GPU passthrough.

---

## Running Tests

```powershell
.\.venv311\Scripts\Activate.ps1
python -m pytest tests/ -v
```

110 tests, ~10 seconds, no GPU required. Tests mock the model inference.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `CUDA: False` | Update NVIDIA driver to >= 550 |
| `adapter_model.safetensors not found` | Run `git lfs pull` |
| `503 Inference engine busy` | Wait and retry — sequential lock |
| `caffe2_nvrtc.dll` error | Reinstall torch with `--index-url .../cu124` |
| Server exits on startup | Check `.env` has valid `AES_SECRET_KEY` |

---

## Project Structure

```
Feever_2.0/
├── api/
│   ├── main.py                  # FastAPI app + lifespan startup validation
│   ├── core/
│   │   ├── model.py             # Qwen3-VL-4B loader, LoRA merge, inference
│   │   ├── normalizer.py        # 1024×1024 letterbox (matches training)
│   │   ├── rule_engine.py       # PhilHealth + hospital DB fuzzy matching
│   │   ├── confidence.py        # Field-level confidence assessment
│   │   ├── postprocess.py       # Date normalization, amount cleanup, cross-validation
│   │   ├── encryption.py        # AES-256-GCM (RA 10173 compliance)
│   │   └── exceptions.py        # Custom exception hierarchy
│   ├── routes/
│   │   ├── health.py            # GET /health
│   │   └── analyze.py           # POST /analyze (main pipeline)
│   └── schemas/
│       ├── request.py           # Pydantic request models
│       └── response.py          # Pydantic response models (TypeScript-like types above)
├── tests/                       # 110 tests (confidence, parsing, normalizer, rule engine, integration)
├── scripts/                     # Data pipeline scripts (build_db, parse_philhealth, merge_adapters)
├── models/
│   ├── reserved/                # Source adapters, hospital DB, PhilHealth annexes
│   └── merged/                  # Runtime adapter (built by merge_adapters.py)
├── data/records/                # Encrypted recordings (gitignored)
├── Dockerfile                   # Multi-stage build with CUDA runtime
├── docker-compose.yml           # GPU passthrough, volume-mounted weights
├── run.ps1                      # Quick-start server script
├── .env.example                 # Template for environment variables
└── requirements.txt             # Python dependencies
```

---

## Future Work

- **PhilHealth Annex C-F** — Excluded benefits (50% adjustment), second case rates, primary care facility rates
- **Vertex AI deployment** — Production hosting on Google Cloud with L4/A100 GPUs
- **Batch processing** — Accept multiple images in a single request
- **WebSocket progress** — Stream processing stages to frontend in real-time
- **User authentication** — JWT-based access control for multi-user environments
