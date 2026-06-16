# Fee-Ver 2.0

Medical billing document analysis API. Accepts an invoice image, runs OCR via a fine-tuned Qwen3-VL-4B model, cross-references against a Philippine hospital services database and PhilHealth Annex A+B rules, and returns a structured discrepancy report.

---

## Prerequisites

Before you begin, make sure you have the following installed:

| Requirement | How to check | Install |
|-------------|-------------|---------|
| **Python 3.11** (not 3.12+, not 3.10) | `python --version` | [python.org](https://www.python.org/downloads/release/python-3119/) |
| **NVIDIA GPU driver >= 550** | `nvidia-smi` | [nvidia.com/drivers](https://www.nvidia.com/Download/index.aspx) |
| **Git LFS** | `git lfs version` | `git lfs install` (one-time) |
| **CUDA Toolkit 12.4+** | `nvcc --version` | Bundled with PyTorch wheel below |

> **Why Python 3.11?** PyTorch does not publish CUDA wheels for Python 3.13+. Python 3.11 is the most stable choice.

### Supported GPUs

| GPU Series | Architecture | Works? | VRAM |
|------------|-------------|--------|------|
| RTX 3060 / 3070 / 3080 / 3090 | Ampere | Yes | 8-24 GB |
| RTX 4060 / 4070 / 4080 / 4090 | Ada Lovelace | Yes | 8-24 GB |
| RTX 5070 / 5080 / 5090 | Blackwell | Yes | 12-32 GB |

**Minimum 8 GB VRAM.** Runtime footprint: ~2.5 GB (4-bit base model) + ~0.26 GB (LoRA adapter) + ~1.5 GB (KV cache + overhead) = **~4.3 GB total**.

---

## Setup (Step by Step)

### Step 1 — Clone and pull LFS files

```powershell
git clone https://github.com/jacob-cob-null/Feever-2.0.git
cd Feever-2.0
git lfs pull
```

> `git lfs pull` downloads the adapter weights (~800 MB total). If you skip this, the server will fail to start.

### Step 2 — Create a Python 3.11 virtual environment

```powershell
# Use your Python 3.11 path (adjust if different)
& "C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python311\python.exe" -m venv .venv311
.\.venv311\Scripts\Activate.ps1
```

Verify you're in the right env:
```powershell
python --version
# Should say: Python 3.11.x
```

### Step 3 — Install PyTorch with CUDA

This is the biggest download (~2.5 GB, one-time). Be patient — it may appear stuck at 99% while verifying the file hash. **Do not cancel it.**

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124 --timeout 600
```

> This single wheel works for **all RTX 30/40/50 series** GPUs.

Verify CUDA is working:
```powershell
python -c "import torch; print(f'PyTorch {torch.__version__}'); print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0)}')"
```

Expected output:
```
PyTorch 2.6.0+cu124
CUDA: True
GPU: NVIDIA GeForce RTX 3060   (or your GPU name)
```

If `CUDA: False`, your NVIDIA driver is too old — update it at [nvidia.com/drivers](https://www.nvidia.com/Download/index.aspx).

### Step 4 — Install project dependencies

```powershell
pip install -r requirements.txt
```

### Step 5 — Run data pipeline (one-time)

These scripts build the lookup tables and prepare the adapter. Takes ~30 seconds.

```powershell
python scripts/build_db.py           # Builds hospital_db.sqlite (3,017 records)
python scripts/parse_philhealth.py   # Parses PhilHealth PDFs -> JSON (8,923 rules)
python scripts/merge_adapters.py     # Prepares composed LoRA adapter (264 MB)
```

### Step 6 — Configure environment variables

```powershell
cp .env.example .env
```

Generate and set your AES encryption key:
```powershell
python -c "from api.core.encryption import generate_key; print(generate_key())"
```

Open `.env` and paste the output as `AES_SECRET_KEY`:
```ini
AES_SECRET_KEY=<paste your generated key here>
```

All other defaults are fine for local development.

---

## Running the Server

### Quick start

```powershell
.\run.ps1
```

### Manual start

```powershell
.\.venv311\Scripts\Activate.ps1
$env:TORCHDYNAMO_DISABLE = "1"
$env:KMP_DUPLICATE_LIB_OK = "TRUE"
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1
```

### What happens on first startup

1. Validates all required files exist (adapter, database, JSONs, AES key)
2. Downloads the base model from HuggingFace (~2.5 GB, one-time, cached after)
3. Loads 4-bit quantized model onto GPU
4. Loads LoRA adapter (264 MB)
5. Runs a warmup inference
6. Logs `"All subsystems OK."` — server is ready

Startup takes ~50-90 seconds depending on your GPU and internet speed.

---

## Testing the API

### Swagger UI (easiest)

Open in your browser: **http://localhost:8000/docs**

### curl

```powershell
# Health check — should return {"status": "ok", ...}
curl http://localhost:8000/health

# Analyze an invoice image
curl -X POST http://localhost:8000/analyze `
  -F "image=@path\to\invoice.png" `
  -F "permission_to_record=false"
```

### Expected health response

```json
{
  "status": "ok",
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

---

## API Endpoints

### `GET /health`

Returns subsystem statuses: model, hospital DB, PhilHealth annexes, encryption, inference lock.

### `POST /analyze`

**Request** — `multipart/form-data`:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image` | file | Yes | JPG / PNG / WebP, max 10 MB |
| `permission_to_record` | bool | No (default: false) | If true, encrypts and saves payload + image to `data/records/` |

**Response** — JSON with:
- `ocr_result` — extracted fields (hospital name, patient, date, amounts)
- `rule_engine` — PhilHealth ceiling checks + hospital DB price matches
- `discrepancies` — flagged violations with severity (HIGH / MEDIUM / LOW)
- `summary` — totals, matches, flags, excess amount
- `recorded` — whether the request was encrypted and saved

**Status codes**: `200` success, `400` bad file, `503` inference busy (try again)

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `CUDA: False` after torch install | Old NVIDIA driver | Update driver to >= 550 |
| Torch install stuck at 99% | Hash verification on 2.5 GB file | Wait 2-3 minutes, don't cancel |
| `No matching distribution for torch` | Wrong Python version | Use Python 3.11, not 3.12+ |
| `adapter_model.safetensors not found` | Didn't run `git lfs pull` | Run `git lfs pull` |
| `503 Inference engine busy` | Another request is processing | Wait and retry (sequential lock) |
| `caffe2_nvrtc.dll` error | CPU-only torch installed | Reinstall with `--index-url .../cu124` |
| Server exits on startup | Missing `.env` or bad AES key | Run Step 6 above |

---

## Project Structure

```
Feever_2.0/
├── api/
│   ├── main.py                # FastAPI app + startup validation
│   ├── core/
│   │   ├── model.py           # Qwen3-VL-4B loader + inference lock
│   │   ├── normalizer.py      # 1024x1024 letterbox (matches training)
│   │   ├── rule_engine.py     # Hospital DB + PhilHealth fuzzy matching
│   │   └── encryption.py      # AES-256-GCM (RA 10173)
│   ├── routes/
│   │   ├── health.py          # GET /health
│   │   └── analyze.py         # POST /analyze
│   └── schemas/
│       ├── request.py         # Pydantic request models
│       └── response.py        # Pydantic response models
├── scripts/
│   ├── setup.ps1              # Automated environment setup
│   ├── build_db.py            # SQL dump -> SQLite (3,017 hospital records)
│   ├── parse_philhealth.py    # PDF -> JSON (4,610 Annex A + 4,313 Annex B)
│   └── merge_adapters.py      # Compose 97:3 LoRA adapter
├── models/
│   ├── reserved/              # Source adapters, database, policy PDFs
│   └── merged/                # Runtime adapter (built by merge_adapters.py)
├── data/records/              # Encrypted recordings (gitignored)
├── run.ps1                    # Quick-start server script
├── .env.example               # Template for environment variables
└── requirements.txt           # Python dependencies (torch installed separately)
```
