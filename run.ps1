<#
.SYNOPSIS
    Start the Fee-Ver 2.0 backend server.
.EXAMPLE
    .\run.ps1
#>

$env:TORCHDYNAMO_DISABLE = "1"
$env:KMP_DUPLICATE_LIB_OK = "TRUE"

if (Test-Path ".venv311\Scripts\Activate.ps1") {
    & .\.venv311\Scripts\Activate.ps1
} elseif (Test-Path ".venv\Scripts\Activate.ps1") {
    & .\.venv\Scripts\Activate.ps1
}

uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1
