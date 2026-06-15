"""GET /health — subsystem status check."""

import time
from datetime import datetime, timezone

from fastapi import APIRouter

from api.core.model import manager
from api.schemas.response import HealthResponse, SubsystemStatus

router = APIRouter()

_start_time: float = time.time()


def set_start_time(t: float) -> None:
    global _start_time
    _start_time = t


# These get injected by main.py at startup
_db_record_count: int = 0
_annex_a_count: int = 0
_annex_b_count: int = 0
_encryption_ok: bool = False


def set_subsystem_info(
    db_records: int, annex_a: int, annex_b: int, encryption_ok: bool
) -> None:
    global _db_record_count, _annex_a_count, _annex_b_count, _encryption_ok
    _db_record_count = db_records
    _annex_a_count = annex_a
    _annex_b_count = annex_b
    _encryption_ok = encryption_ok


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    # Model
    if manager.is_loaded:
        used, total = manager.get_vram_info()
        model_status = SubsystemStatus(
            status="loaded",
            device=str(manager.device),
            vram_used_mb=used,
            vram_total_mb=total,
        )
    else:
        model_status = SubsystemStatus(status="error")

    # Hospital DB
    db_status = SubsystemStatus(
        status="ok" if _db_record_count > 0 else "error",
        record_count=_db_record_count,
    )

    # PhilHealth
    ph_status = SubsystemStatus(
        status="ok" if (_annex_a_count > 0 and _annex_b_count > 0) else "error",
        annex_a_rules=_annex_a_count,
        annex_b_rules=_annex_b_count,
    )

    # Encryption
    enc_status = SubsystemStatus(
        status="ok" if _encryption_ok else "error",
        algorithm="AES-256-GCM",
    )

    # Inference lock
    lock_status = SubsystemStatus(
        status="held" if manager.lock_held else "free",
    )

    # Overall
    all_ok = (
        manager.is_loaded
        and _db_record_count > 0
        and _annex_a_count > 0
        and _annex_b_count > 0
        and _encryption_ok
    )
    overall = "ok" if all_ok else "degraded"

    return HealthResponse(
        status=overall,
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=int(time.time() - _start_time),
        subsystems={
            "model": model_status,
            "hospital_db": db_status,
            "philhealth_annex": ph_status,
            "encryption": enc_status,
            "inference_lock": lock_status,
        },
    )
