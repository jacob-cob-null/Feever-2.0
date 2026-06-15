"""Fee-Ver 2.0 — FastAPI application with lifespan startup validation."""

import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("feever")

ROOT = Path(__file__).resolve().parent.parent


def _resolve(env_key: str, default: str) -> Path:
    return ROOT / os.getenv(env_key, default)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup validation (PRD Section 11) then yield."""
    start = time.time()

    # --- 1. Verify merged adapter exists ---
    model_path = _resolve("MODEL_PATH", "models/merged/qwen3vl_merged")
    if not (model_path / "adapter_model.safetensors").exists():
        logger.error("Merged adapter not found at %s", model_path)
        sys.exit(1)
    logger.info("Merged adapter found: %s", model_path)

    # --- 2. Verify hospital DB ---
    db_path = _resolve("HOSPITAL_DB_PATH", "models/reserved/hospital_db.sqlite")
    if not db_path.exists():
        logger.error("Hospital DB not found at %s", db_path)
        sys.exit(1)
    logger.info("Hospital DB found: %s", db_path)

    # --- 3. Verify PhilHealth JSONs ---
    annex_a_path = _resolve(
        "PHILHEALTH_ANNEX_A_PATH", "models/reserved/philhealth_annex_a.json"
    )
    annex_b_path = _resolve(
        "PHILHEALTH_ANNEX_B_PATH", "models/reserved/philhealth_annex_b.json"
    )
    if not annex_a_path.exists() or not annex_b_path.exists():
        logger.error("PhilHealth annex JSONs missing")
        sys.exit(1)
    logger.info("PhilHealth annexes found")

    # --- 4. Verify AES key ---
    from api.core.encryption import load_key

    aes_secret = os.getenv("AES_SECRET_KEY", "")
    try:
        aes_key = load_key(aes_secret)
        encryption_ok = True
    except Exception as e:
        logger.error("Invalid AES_SECRET_KEY: %s", e)
        sys.exit(1)
    logger.info("AES-256-GCM key loaded")

    # --- 5. Open SQLite read-only, confirm table ---
    import sqlite3

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    db_count = conn.execute("SELECT COUNT(*) FROM medical_services").fetchone()[0]
    conn.close()
    logger.info("Hospital DB: %d records", db_count)

    # --- 6. Load Annex A + B into rule engine ---
    from api.core.rule_engine import RuleEngine

    rule_engine = RuleEngine(
        db_path=db_path,
        annex_a_path=annex_a_path,
        annex_b_path=annex_b_path,
        hospital_threshold=float(os.getenv("HOSPITAL_FUZZY_THRESHOLD", "80")),
        philhealth_threshold=float(os.getenv("PHILHEALTH_FUZZY_THRESHOLD", "82")),
        price_tolerance=float(os.getenv("PRICE_DELTA_TOLERANCE", "0.05")),
    )

    # --- 7. Load model onto CUDA ---
    from api.core.model import manager

    logger.info("Loading model (this may take a minute)...")
    manager.load(model_path)

    # --- 8. Warmup inference ---
    manager.warmup()

    # --- Inject dependencies into routes ---
    from api.routes.analyze import set_dependencies
    from api.routes.health import set_start_time, set_subsystem_info

    records_dir = ROOT / "data" / "records"
    set_dependencies(rule_engine, aes_key, records_dir)
    set_start_time(start)
    set_subsystem_info(
        db_records=db_count,
        annex_a=len(rule_engine.annex_a),
        annex_b=len(rule_engine.annex_b),
        encryption_ok=encryption_ok,
    )

    # --- 9. All systems go ---
    elapsed = time.time() - start
    logger.info("All subsystems OK. Startup took %.1fs", elapsed)

    yield

    logger.info("Shutting down")


# --- App ---

app = FastAPI(
    title="Fee-Ver 2.0",
    description="Medical billing document analysis API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.routes.analyze import router as analyze_router
from api.routes.health import router as health_router

app.include_router(health_router)
app.include_router(analyze_router)
