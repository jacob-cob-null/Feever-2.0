import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Chandra Settings
    CHANDRA_MODEL_ID = os.getenv("CHANDRA_MODEL_ID", "datalab-to/chandra-ocr-2")
    CHANDRA_DEVICE = os.getenv("CHANDRA_DEVICE", "cuda")
    CHANDRA_QUANTIZATION = os.getenv("CHANDRA_QUANTIZATION", "4bit")
    CHANDRA_BATCH_SIZE = int(os.getenv("CHANDRA_BATCH_SIZE", "1"))
    CHANDRA_TIMEOUT = int(os.getenv("CHANDRA_TIMEOUT", "120"))
    
    # DB
    DB_URL = os.getenv("DB_URL", "sqlite:///./medical_services.db")
    
    # Pipeline limits
    PARALLEL_PROCESSING = os.getenv("PARALLEL_PROCESSING", "false").lower() == "true"
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))
    RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))

config = Config()
