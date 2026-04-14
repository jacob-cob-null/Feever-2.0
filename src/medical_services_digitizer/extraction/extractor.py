from typing import Dict, List
from .qwen_client import QwenVLClient, OCRInferenceError, OCROutOfMemoryError
from .validators import Validators
import logging
from ..config import config

logger = logging.getLogger(__name__)

class MedicalServiceExtractor:
    def __init__(self):
        self.client = QwenVLClient(
            api_base=config.OLLAMA_API_BASE,
            model=config.OLLAMA_MODEL,
            api_key=config.OLLAMA_API_KEY,
            timeout=config.OLLAMA_TIMEOUT,
            temperature=config.OLLAMA_TEMPERATURE,
        )
        self.validators = Validators()

    def get_ocr_status(self) -> Dict:
        return self.client.get_status()
        
    def extract_from_image(self, image_path: str, validate: bool = True, retry_attempts: int = config.RETRY_ATTEMPTS) -> List[Dict]:
        for attempt in range(retry_attempts):
            attempt_number = attempt + 1
            try:
                result = self.client.extract_from_image(image_path)
                services = result if isinstance(result, list) else [result]
                
                valid_services = []
                for s in services:
                    if validate:
                        is_valid, errors = self.validators.validate(s)
                        if not is_valid:
                            logger.warning(f"Validation failed for service in {image_path}: {errors}")
                            continue
                    
                    s['source_image'] = image_path
                    valid_services.append(s)
                
                return valid_services
            except OCROutOfMemoryError as error:
                logger.error(
                    "Extraction attempt %s/%s failed due to OOM: %s",
                    attempt_number,
                    retry_attempts,
                    error,
                )
                break
            except OCRInferenceError as error:
                logger.warning(
                    "Extraction attempt %s/%s failed: %s",
                    attempt_number,
                    retry_attempts,
                    error,
                )
            except Exception as error:
                logger.warning(
                    "Extraction attempt %s/%s failed with unexpected error: %s",
                    attempt_number,
                    retry_attempts,
                    error,
                )
        
        logger.error(f"All {retry_attempts} attempts failed for {image_path}")
        return []
