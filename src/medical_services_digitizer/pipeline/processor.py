import concurrent.futures
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List
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
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
    PDF_EXTENSION = ".pdf"

    def __init__(self, images_dir: str, output_db: str):
        self.images_dir = images_dir
        self.digitizer = MedicalServicesDigitizer(db_url=f"sqlite:///{output_db}")
        self._temp_dirs: List[str] = []

    def _discover_inputs(self, directory: str) -> List[str]:
        discovered: List[str] = []
        for path in Path(directory).rglob("*"):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix in self.IMAGE_EXTENSIONS or suffix == self.PDF_EXTENSION:
                discovered.append(str(path))
        return sorted(discovered)

    def _render_pdf_to_images(self, pdf_path: str) -> List[str]:
        try:
            import fitz
        except Exception as error:
            raise RuntimeError(
                "PyMuPDF is required for PDF input. Install dependency 'pymupdf'."
            ) from error

        rendered_images: List[str] = []
        temp_dir = tempfile.mkdtemp(prefix="medical_pdf_pages_")
        self._temp_dirs.append(temp_dir)

        with fitz.open(pdf_path) as document:
            for page_index, page in enumerate(document, start=1):
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                output_image = os.path.join(
                    temp_dir,
                    f"{Path(pdf_path).stem}_page_{page_index}.png",
                )
                pixmap.save(output_image)
                rendered_images.append(output_image)

        return rendered_images

    def _expand_inputs_to_images(self, input_paths: List[str]) -> List[str]:
        image_paths: List[str] = []
        for path in input_paths:
            suffix = Path(path).suffix.lower()
            if suffix in self.IMAGE_EXTENSIONS:
                image_paths.append(path)
                continue
            if suffix == self.PDF_EXTENSION:
                try:
                    image_paths.extend(self._render_pdf_to_images(path))
                except Exception as error:
                    logger.error("Failed to render PDF %s: %s", path, error)
        return image_paths

    def _cleanup_temp_dirs(self) -> None:
        for temp_dir in self._temp_dirs:
            shutil.rmtree(temp_dir, ignore_errors=True)
        self._temp_dirs.clear()

    def _sanitize_output_filename(self, folder_name: str) -> str:
        safe = "".join(c if c.isalnum() or c in {"-", "_", " "} else "_" for c in folder_name).strip()
        return safe.replace(" ", "_") or "unknown_source"
        
    def process_all(self) -> Dict:
        input_paths = self._discover_inputs(self.images_dir)
        image_paths = self._expand_inputs_to_images(input_paths)

        logger.info(
            "Found %s supported files (%s rendered images) in %s",
            len(input_paths),
            len(image_paths),
            self.images_dir,
        )

        try:
            res = self.digitizer.process_batch(image_paths, parallel=False)
            return {
                "total_services": len(res["services"]),
                "success": res["success"],
                "failed": res["failed"],
                "inputs": len(input_paths),
                "rendered_images": len(image_paths),
            }
        finally:
            self._cleanup_temp_dirs()

    def process_raw_directories_to_sql(
        self,
        raw_root_dir: str,
        sql_output_dir: str,
        start_service_id: int = 1,
    ) -> Dict:
        os.makedirs(sql_output_dir, exist_ok=True)

        next_service_id = start_service_id
        folder_summaries: List[Dict] = []
        sql_files: List[str] = []

        source_folders = sorted(
            folder for folder in Path(raw_root_dir).iterdir() if folder.is_dir()
        )

        for folder in source_folders:
            source_name = folder.name
            input_paths = self._discover_inputs(str(folder))
            image_paths = self._expand_inputs_to_images(input_paths)

            logger.info(
                "Processing source folder '%s' with %s files (%s rendered images)",
                source_name,
                len(input_paths),
                len(image_paths),
            )

            try:
                if image_paths:
                    result = self.digitizer.process_batch(image_paths, parallel=False)
                else:
                    result = {"success": 0, "failed": 0, "services": []}

                standardized_services: List[Dict] = []
                for service in result["services"]:
                    standardized_services.append(
                        {
                            "service_ID": next_service_id,
                            "service_Name": service.get("service_name", "Unknown Service"),
                            "service_Origin": source_name,
                            "service_Price": service.get("price", 0.0),
                        }
                    )
                    next_service_id += 1

                sql_path = os.path.join(
                    sql_output_dir,
                    f"{self._sanitize_output_filename(source_name)}.sql",
                )
                self.digitizer.db_manager.export_standardized_sql(sql_path, standardized_services)
                sql_files.append(sql_path)

                folder_summaries.append(
                    {
                        "source": source_name,
                        "inputs": len(input_paths),
                        "rendered_images": len(image_paths),
                        "services": len(standardized_services),
                        "success": result["success"],
                        "failed": result["failed"],
                        "sql_file": sql_path,
                    }
                )
            finally:
                self._cleanup_temp_dirs()

        return {
            "folders": len(folder_summaries),
            "total_services": sum(item["services"] for item in folder_summaries),
            "files_generated": sql_files,
            "next_service_id": next_service_id,
            "details": folder_summaries,
        }
