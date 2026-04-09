import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class Config:
    def __init__(self):
        # Qwen 3 VL via Ollama OpenAI-compatible endpoint
        self.OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://127.0.0.1:11434/v1").strip()
        self.OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3-vl:8b-instruct").strip()
        self.OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama").strip()
        self.OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
        self.OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0"))

        # DB
        self.DB_URL = os.getenv("DB_URL", "sqlite:///./data/medical_services.db")

        # Pipeline limits
        self.PARALLEL_PROCESSING = os.getenv("PARALLEL_PROCESSING", "false").lower() == "true"
        self.MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))
        self.RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))

        logger.info(
            "OCR config loaded: ollama_api_base=%s ollama_model=%s timeout=%s temperature=%s",
            self.OLLAMA_API_BASE,
            self.OLLAMA_MODEL,
            self.OLLAMA_TIMEOUT,
            self.OLLAMA_TEMPERATURE,
        )

config = Config()
