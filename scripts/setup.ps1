<#
.SYNOPSIS
    Fee-Ver 2.0 environment setup — installs Python dependencies + CUDA PyTorch.

.DESCRIPTION
    Detects your NVIDIA GPU and installs the correct PyTorch wheel:
      - RTX 30/40 series (Ampere/Ada): CUDA 12.4
      - RTX 50 series (Blackwell):     CUDA 12.4
    Falls back to CPU-only torch if no NVIDIA GPU is detected.

.NOTES
    Prerequisites:
      - Python 3.11+
      - NVIDIA driver >= 550 (run 'nvidia-smi' to check)
      - Git LFS installed ('git lfs install')

.EXAMPLE
    .\scripts\setup.ps1
#>

$ErrorActionPreference = "Stop"

Write-Host "`n=== Fee-Ver 2.0 Setup ===" -ForegroundColor Cyan

# --- Check Python ---
$pyVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found. Install Python 3.11+." -ForegroundColor Red
    exit 1
}
Write-Host "Python: $pyVersion"

# --- Create venv if needed ---
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}
Write-Host "Activating .venv..."
& .\.venv\Scripts\Activate.ps1

# --- Detect GPU ---
$hasNvidia = $false
try {
    $smiOutput = nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>&1
    if ($LASTEXITCODE -eq 0) {
        $hasNvidia = $true
        Write-Host "GPU detected: $smiOutput" -ForegroundColor Green
    }
} catch {
    Write-Host "No NVIDIA GPU detected." -ForegroundColor Yellow
}

# --- Install PyTorch ---
if ($hasNvidia) {
    Write-Host "`nInstalling PyTorch with CUDA 12.4 (supports RTX 30/40/50 series)..."
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
} else {
    Write-Host "`nInstalling PyTorch (CPU only — inference will be slow)..." -ForegroundColor Yellow
    pip install torch torchvision
}

# --- Install remaining dependencies ---
Write-Host "`nInstalling project dependencies..."
pip install -r requirements.txt

# --- Run Phase 1 setup scripts ---
Write-Host "`n=== Running data pipeline ===" -ForegroundColor Cyan

if (-not (Test-Path "models\reserved\hospital_db.sqlite")) {
    Write-Host "Building hospital database..."
    python scripts\build_db.py
} else {
    Write-Host "hospital_db.sqlite already exists, skipping."
}

if (-not (Test-Path "models\reserved\philhealth_annex_a.json")) {
    Write-Host "Parsing PhilHealth PDFs..."
    python scripts\parse_philhealth.py
} else {
    Write-Host "PhilHealth JSONs already exist, skipping."
}

if (-not (Test-Path "models\merged\qwen3vl_merged\adapter_model.safetensors")) {
    Write-Host "Preparing merged adapter..."
    python scripts\merge_adapters.py
} else {
    Write-Host "Merged adapter already exists, skipping."
}

# --- Generate .env if missing ---
if (-not (Test-Path ".env")) {
    Write-Host "`nGenerating .env from .env.example..."
    Copy-Item .env.example .env
    $key = python -c "from api.core.encryption import generate_key; print(generate_key())"
    (Get-Content .env) -replace '^AES_SECRET_KEY=$', "AES_SECRET_KEY=$key" | Set-Content .env
    Write-Host "Generated AES key in .env" -ForegroundColor Green
} else {
    Write-Host ".env already exists, skipping."
}

# --- Verify torch + CUDA ---
Write-Host "`n=== Verification ===" -ForegroundColor Cyan
python -c "import torch; print(f'PyTorch {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"

Write-Host "`n=== Setup complete ===" -ForegroundColor Green
Write-Host "Start the server with:"
Write-Host '  $env:TORCHDYNAMO_DISABLE = "1"' -ForegroundColor White
Write-Host '  $env:KMP_DUPLICATE_LIB_OK = "TRUE"' -ForegroundColor White
Write-Host '  uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1' -ForegroundColor White
Write-Host ""
