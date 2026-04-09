import json
import logging
import os
import re
from typing import Dict, List, Optional
import importlib.util

logger = logging.getLogger(__name__)

class ChandraOCRClient:
    def __init__(self, batch_size: int = 1, quantization: str = "4bit", device: str = "cuda", timeout: int = 120):
        self.batch_size = batch_size
        self.quantization = quantization
        self.device = device
        self.timeout = timeout
        
        self._model = None
        self._batch_input_item_cls = None
        self._backend = "mock"
        
        if self.is_available():
            try:
                # Newer chandra-ocr packages expose module `chandra` (not `chandra_ocr`).
                if importlib.util.find_spec("chandra") is not None:
                    from chandra.model import InferenceManager
                    from chandra.model.schema import BatchInputItem

                    os.environ["TORCH_DEVICE"] = self.device
                    self._model = InferenceManager(method="hf")
                    self._batch_input_item_cls = BatchInputItem
                    self._backend = "chandra_hf"
                    logger.info(f"Chandra OCR (hf backend) loaded successfully on device='{self.device}'.")
                else:
                    from chandra_ocr import ChandraOCR

                    self._model = ChandraOCR(
                        batch_size=self.batch_size,
                        quantization=self.quantization,
                        max_tokens=2048,
                        device=self.device,
                    )
                    self._backend = "chandra_ocr_legacy"
                    logger.info("Chandra OCR (legacy backend) loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load Chandra OCR: {e}")
        else:
            logger.warning("Chandra OCR package not found. Client is in mock mode.")
            
    def is_available(self) -> bool:
        return (
            importlib.util.find_spec("chandra") is not None
            or importlib.util.find_spec("chandra_ocr") is not None
        )

    def _extract_json_payload(self, text: str) -> Optional[str]:
        candidate = text.strip()

        # Remove markdown fences when present.
        if candidate.startswith("```"):
            candidate = re.sub(r"^```(?:json)?\\s*", "", candidate)
            candidate = re.sub(r"\\s*```$", "", candidate)

        # Try direct JSON first.
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            pass

        # Fall back to first top-level object or array in the text.
        object_start = candidate.find("{")
        object_end = candidate.rfind("}")
        if object_start != -1 and object_end != -1 and object_end > object_start:
            snippet = candidate[object_start : object_end + 1]
            try:
                json.loads(snippet)
                return snippet
            except Exception:
                pass

        array_start = candidate.find("[")
        array_end = candidate.rfind("]")
        if array_start != -1 and array_end != -1 and array_end > array_start:
            snippet = candidate[array_start : array_end + 1]
            try:
                json.loads(snippet)
                return snippet
            except Exception:
                pass

        return None

    def _normalize_services(self, parsed: object) -> List[Dict]:
        if isinstance(parsed, dict) and isinstance(parsed.get("services"), list):
            services = parsed["services"]
        elif isinstance(parsed, list):
            services = parsed
        elif isinstance(parsed, dict):
            services = [parsed]
        else:
            return []

        normalized: List[Dict] = []
        for item in services:
            if not isinstance(item, dict):
                continue

            price = item.get("price", item.get("rates", item.get("amount")))
            try:
                if price is None:
                    continue
                price = float(price)
            except (TypeError, ValueError):
                continue

            service_name = item.get("service_name") or item.get("description") or item.get("service")
            if not service_name:
                continue

            normalized.append(
                {
                    "service_name": str(service_name),
                    "price": price,
                    "facility": item.get("facility") or "Unknown Facility",
                    "category": item.get("category"),
                    "currency": item.get("currency") or "PHP",
                    "description": item.get("description") or str(service_name),
                }
            )

        return normalized

    def _extract_with_hf_backend(self, image_path: str) -> List[Dict]:
        from PIL import Image

        prompt = (
            "Extract medical service line items from this image and return ONLY strict JSON. "
            "Expected format: {\"services\":[{\"service_name\":\"...\",\"price\":123.45,"
            "\"facility\":\"...\",\"category\":\"...\",\"currency\":\"PHP\","
            "\"description\":\"...\"}]}. "
            "If no medical service items are present, return {\"services\":[]}. "
            "Do not wrap JSON in markdown or add extra text."
        )

        image = Image.open(image_path).convert("RGB")
        item = self._batch_input_item_cls(image=image, prompt=prompt)
        results = self._model.generate([item], max_output_tokens=1024)
        if not results:
            return []

        payload = self._extract_json_payload(results[0].raw or "")
        if not payload:
            logger.warning("Could not parse structured JSON from Chandra output.")
            return []

        parsed = json.loads(payload)
        return self._normalize_services(parsed)
        
    def extract_from_image(self, image_path: str) -> List[Dict] | Dict:
        if self._model and self._backend == "chandra_hf":
            try:
                return self._extract_with_hf_backend(image_path)
            except Exception as e:
                logger.error(f"Error extracting from {image_path}: {e}")
                raise e

        if self._model and self._backend == "chandra_ocr_legacy":
            try:
                result = self._model.process(image_path)
                if isinstance(result, str):
                    return json.loads(result)
                return result
            except Exception as e:
                logger.error(f"Error extracting from {image_path}: {e}")
                raise e
        else:
            logger.info(f"Mock extraction for {image_path}")
            return {
                "service_name": "MOCK CT Scan",
                "price": 5000.00,
                "facility": "MOCK Hospital",
                "category": "Imaging",
                "currency": "PHP",
                "description": "Mocked extraction due to missing chandra_ocr"
            }
