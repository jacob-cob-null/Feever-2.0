from typing import Dict, List, Tuple
from .chandra_client import ChandraOCRClient
from .validators import Validators
import logging
from ..config import config

logger = logging.getLogger(__name__)

class MedicalServiceExtractor:
    def __init__(self):
        self.client = ChandraOCRClient(
            batch_size=config.CHANDRA_BATCH_SIZE,
            quantization=config.CHANDRA_QUANTIZATION,
            device=config.CHANDRA_DEVICE,
            timeout=config.CHANDRA_TIMEOUT
        )
        self.validators = Validators()
        
    def extract_from_image(self, image_path: str, validate: bool = True, retry_attempts: int = config.RETRY_ATTEMPTS) -> List[Dict]:
        for attempt in range(retry_attempts):
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
            except Exception as e:
                logger.warning(f"Extraction attempt {attempt+1}/{retry_attempts} failed: {e}")
        
        logger.error(f"All {retry_attempts} attempts failed for {image_path}")
        return []
