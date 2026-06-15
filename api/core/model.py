"""Model loader, inference lock, and CUDA management.

Loads the 4-bit BnB base model + composed LoRA adapter.
Runtime VRAM: ~2.5 GB base + ~0.26 GB adapter + ~1.5 GB overhead = ~4.3 GB.
"""

import json
import logging
import threading
from pathlib import Path

import torch
from PIL import Image
from peft import PeftModel
from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = (
    "You are a document extraction assistant. Given the image of an invoice "
    "or billing document, extract the following fields and return them as a "
    "single JSON object with exactly these keys: date, patient_name, "
    "philhealth_number, diagnosis_code, procedure_code, total_amount, "
    "philhealth_benefit, balance_due. Use null for any field not present in "
    "the document. Return only the JSON object — no explanation, no markdown."
)


class ModelManager:
    """Singleton-style model holder with inference lock."""

    def __init__(self):
        self.model = None
        self.processor = None
        self.device = None
        self.lock = threading.Lock()
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def lock_held(self) -> bool:
        # Try to acquire without blocking; if we can't, it's held
        if self.lock.acquire(blocking=False):
            self.lock.release()
            return False
        return True

    def load(self, adapter_path: str | Path) -> None:
        """Load base model + LoRA adapter onto GPU."""
        adapter_path = Path(adapter_path)
        config_path = adapter_path / "adapter_config.json"

        if not config_path.exists():
            raise FileNotFoundError(f"adapter_config.json not found in {adapter_path}")

        with open(config_path) as f:
            adapter_cfg = json.load(f)

        base_model_id = adapter_cfg["base_model_name_or_path"]
        logger.info("Loading base model: %s", base_model_id)

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )

        base_model = AutoModelForImageTextToText.from_pretrained(
            base_model_id,
            quantization_config=bnb_config,
            device_map="auto",
            torch_dtype=torch.float16,
        )

        logger.info("Loading LoRA adapter from: %s", adapter_path)
        self.model = PeftModel.from_pretrained(
            base_model,
            str(adapter_path),
            is_trainable=False,
        )
        self.model.eval()

        self.processor = AutoProcessor.from_pretrained(
            str(adapter_path),
            trust_remote_code=True,
        )

        self.device = next(self.model.parameters()).device
        self._loaded = True
        logger.info("Model loaded on %s", self.device)

    def warmup(self) -> None:
        """Run a throwaway inference to prime CUDA kernels."""
        if not self._loaded:
            return
        logger.info("Running warmup inference...")
        dummy = Image.new("RGB", (64, 64), (245, 245, 245))
        try:
            self.run_inference(dummy)
        except Exception:
            logger.warning("Warmup inference produced no valid JSON (expected)")
        finally:
            self._flush_cuda()
        logger.info("Warmup complete")

    def run_inference(self, pil_image: Image.Image, max_new_tokens: int = 512) -> dict:
        """Run OCR inference on a PIL image. Returns parsed JSON dict.

        Caller must hold self.lock before calling this.
        """
        if not self._loaded:
            raise RuntimeError("Model not loaded")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": pil_image},
                    {"type": "text", "text": EXTRACTION_PROMPT},
                ],
            }
        ]

        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        inputs = self.processor(
            text=[text],
            images=[pil_image],
            return_tensors="pt",
            padding=True,
        ).to(self.device)

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                temperature=None,
                top_p=None,
            )

        # Decode only the generated tokens (skip input)
        generated = output_ids[0][inputs["input_ids"].shape[1]:]
        raw_text = self.processor.decode(generated, skip_special_tokens=True)

        return self._parse_output(raw_text)

    def get_vram_info(self) -> tuple[int, int]:
        """Return (used_mb, total_mb) for the model's CUDA device."""
        if not self._loaded or not torch.cuda.is_available():
            return 0, 0
        idx = self.device.index if self.device.index is not None else 0
        used = torch.cuda.memory_allocated(idx) // (1024 * 1024)
        total = torch.cuda.get_device_properties(idx).total_mem // (1024 * 1024)
        return used, total

    def _flush_cuda(self) -> None:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    @staticmethod
    def _parse_output(raw: str) -> dict:
        """Extract JSON from model output, handling markdown fences."""
        text = raw.strip()
        if text.startswith("```"):
            # Strip ```json ... ``` fences
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        return json.loads(text)


# Module-level singleton
manager = ModelManager()
