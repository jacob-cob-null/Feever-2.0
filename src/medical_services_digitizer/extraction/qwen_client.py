import json
import logging
import mimetypes
from base64 import b64encode
from typing import Dict, List

logger = logging.getLogger(__name__)


class OCRClientError(Exception):
    """Base exception for OCR client errors."""


class OCRBackendLoadError(OCRClientError):
    """Raised when an OCR backend fails to initialize."""


class OCRInferenceError(OCRClientError):
    """Raised when OCR inference fails."""


class OCROutOfMemoryError(OCRInferenceError):
    """Raised when OCR inference fails due to memory pressure."""


class QwenVLClient:
    def __init__(
        self,
        api_base: str = "http://127.0.0.1:11434/v1",
        model: str = "qwen3-vl:8b-instruct",
        api_key: str = "ollama",
        timeout: int = 120,
        temperature: float = 0.0,
    ):
        self.api_base = api_base
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.temperature = temperature

        self._client = None
        self._backend = "mock"
        self._backend_init_errors: List[str] = []

        self._initialize_backend()
        logger.info("OCR runtime status: %s", self.get_status())

    def _record_backend_error(self, error: Exception) -> None:
        message = str(error)
        self._backend_init_errors.append(message)
        logger.warning("Qwen backend unavailable: %s", error)

    def _initialize_backend(self) -> None:
        if not self.model:
            self._record_backend_error(OCRBackendLoadError("OLLAMA_MODEL is empty"))
            return

        try:
            from openai import OpenAI
        except Exception as error:
            self._record_backend_error(
                OCRBackendLoadError(f"openai package is required for Ollama OpenAI endpoint: {error}")
            )
            return

        try:
            client = OpenAI(base_url=self.api_base, api_key=self.api_key, timeout=self.timeout)
            models = client.models.list()
        except Exception as error:
            self._record_backend_error(
                OCRBackendLoadError(f"Cannot reach Ollama OpenAI endpoint at '{self.api_base}': {error}")
            )
            return

        model_ids = [item.id for item in getattr(models, "data", []) if getattr(item, "id", None)]
        if model_ids and self.model not in model_ids:
            self._record_backend_error(
                OCRBackendLoadError(
                    f"Configured model '{self.model}' not found. Available models: {model_ids}"
                )
            )
            return

        self._client = client
        self._backend = "ollama_openai_vision"
        logger.info("Qwen backend loaded with model='%s' at '%s'.", self.model, self.api_base)

    def get_status(self) -> Dict[str, object]:
        return {
            "backend": self._backend,
            "model": self.model,
            "api_base": self.api_base,
            "timeout": self.timeout,
            "temperature": self.temperature,
            "mock_mode": self._backend == "mock",
            "backend_init_errors": list(self._backend_init_errors),
        }

    def _extract_json_payload(self, text: str) -> str | None:
        candidate = text.strip()

        if candidate.startswith("```"):
            lines = candidate.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            candidate = "\n".join(lines).strip()

        try:
            json.loads(candidate)
            return candidate
        except Exception:
            pass

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

    def _extract_with_ollama_backend(self, image_path: str) -> List[Dict]:
        prompt = (
            "Extract medical service line items from this image and return ONLY strict JSON. "
            "Expected format: {\"services\":[{\"service_name\":\"...\",\"price\":123.45,"
            "\"facility\":\"...\",\"category\":\"...\",\"currency\":\"PHP\","
            "\"description\":\"...\"}]}. "
            "If no medical service items are present, return {\"services\":[]}. "
            "Do not wrap JSON in markdown or add extra text."
        )

        mime_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
        with open(image_path, "rb") as image_file:
            image_b64 = b64encode(image_file.read()).decode("ascii")

        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{image_b64}"},
                        },
                    ],
                }
            ],
            temperature=self.temperature,
            max_tokens=1024,
        )

        raw_content = response.choices[0].message.content
        if isinstance(raw_content, list):
            chunks = []
            for part in raw_content:
                if isinstance(part, dict):
                    chunks.append(str(part.get("text", "")))
                else:
                    chunks.append(str(getattr(part, "text", "")))
            raw_text = "".join(chunks)
        else:
            raw_text = str(raw_content or "")

        payload = self._extract_json_payload(raw_text)
        if not payload:
            raise OCRInferenceError("Could not parse structured JSON from Qwen output.")

        parsed = json.loads(payload)
        return self._normalize_services(parsed)

    def _classify_runtime_error(self, image_path: str, error: Exception) -> OCRInferenceError:
        error_name = type(error).__name__.lower()
        message = str(error).lower()
        if "outofmemory" in error_name or "out of memory" in message:
            return OCROutOfMemoryError(f"OOM while extracting from {image_path}: {error}")
        return OCRInferenceError(f"Extraction failed for {image_path}: {error}")

    def extract_from_image(self, image_path: str) -> List[Dict] | Dict:
        if self._backend == "ollama_openai_vision" and self._client is not None:
            try:
                return self._extract_with_ollama_backend(image_path)
            except Exception as error:
                classified_error = self._classify_runtime_error(image_path, error)
                logger.error(str(classified_error))
                raise classified_error from error

        logger.info("Mock extraction for %s", image_path)
        return {
            "service_name": "MOCK CT Scan",
            "price": 5000.00,
            "facility": "MOCK Hospital",
            "category": "Imaging",
            "currency": "PHP",
            "description": "Mocked extraction because Ollama Qwen endpoint is unavailable",
        }
