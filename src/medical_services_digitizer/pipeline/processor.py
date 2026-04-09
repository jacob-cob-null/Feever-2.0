import os
import glob
from typing import Dict, List
import concurrent.futures
import logging
from ..config import config
from ..extraction.extractor import MedicalServiceExtractor
from ..database.operations import DatabaseManager

logger = logging.getLogger(__name__)

class MedicalServicesDigitizer:
    def __init__(self, db_url: str = config.DB_URL):
        self.extractor = MedicalServiceExtractor()
        self.db_manager = DatabaseManager(db_url)

    def get_ocr_status(self) -> Dict:
        return self.extractor.get_ocr_status()
        
    def process_image(self, image_path: str) -> Dict:
        services = self.extractor.extract_from_image(image_path)
        if services:
            self.db_manager.insert_batch(services)
        return {
            "services": services,
            "count": len(services),
            "ocr_status": self.get_ocr_status(),
        }

    def process_batch(self, image_paths: List[str], parallel: bool = config.PARALLEL_PROCESSING, max_workers: int = config.MAX_WORKERS) -> Dict:
        results = {"success": 0, "failed": 0, "services": []}
        
        if parallel:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_image = {executor.submit(self.process_image, img): img for img in image_paths}
                for future in concurrent.futures.as_completed(future_to_image):
                    img = future_to_image[future]
                    try:
                        res = future.result()
                        if res["count"] > 0:
                            results["success"] += 1
                            results["services"].extend(res["services"])
                        else:
                            results["failed"] += 1
                    except Exception as e:
                        logger.error(f"Failed to process {img}: {e}")
                        results["failed"] += 1
        else:
            for img in image_paths:
                try:
                    res = self.process_image(img)
                    if res["count"] > 0:
                        results["success"] += 1
                        results["services"].extend(res["services"])
                    else:
                        results["failed"] += 1
                except Exception as e:
                    logger.error(f"Failed to process {img}: {e}")
                    results["failed"] += 1
                    
        return results
        
    def query(self, filters: Dict) -> List[Dict]:
        facility = filters.get("facility")
        if facility:
            services = self.db_manager.query_by_facility(facility)
            # Remove SQLAlchemy internal state before returning
            ret = []
            for s in services:
                d = s.__dict__.copy()
                d.pop('_sa_instance_state', None)
                ret.append(d)
            return ret
        return []

class BatchProcessor:
    def __init__(self, images_dir: str, output_db: str):
        self.images_dir = images_dir
        self.digitizer = MedicalServicesDigitizer(db_url=f"sqlite:///{output_db}")
        
    def process_all(self) -> Dict:
        image_paths = []
        for ext in ('*.png', '*.jpg', '*.jpeg'):
            image_paths.extend(glob.glob(os.path.join(self.images_dir, ext)))
        
        logger.info(f"Found {len(image_paths)} images in {self.images_dir}")
        res = self.digitizer.process_batch(image_paths)
        return {
            "total_services": len(res["services"]),
            "success": res["success"],
            "failed": res["failed"]
        }
