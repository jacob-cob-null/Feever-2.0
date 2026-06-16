"""Model loader, inference lock, and CUDA management.

Loads the pre-quantized 4-bit BnB base model + composed LoRA adapter.
Pinned to transformers==5.5.0 to match training environment.
Runtime VRAM: ~2.5 GB base + ~0.26 GB adapter + ~1.5 GB overhead = ~4.3 GB.
"""

import json
import logging
import re
import threading
from pathlib import Path

import bitsandbytes as bnb
import torch
from PIL import Image
from peft import PeftModel
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

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
        has_cuda = torch.cuda.is_available()
        logger.info(
            "Loading base model: %s (CUDA: %s%s)",
            base_model_id,
            has_cuda,
            f" - {torch.cuda.get_device_name(0)}" if has_cuda else "",
        )

        # The base model is already pre-quantized in 4-bit BnB by unsloth.
        # Do NOT pass quantization_config or torch_dtype — just load it directly.
        # Use the exact class from adapter_config.json auto_mapping.
        base_model = Qwen3VLForConditionalGeneration.from_pretrained(
            base_model_id,
            device_map={"": 0} if has_cuda else "cpu",
        )

        # The unsloth pre-quantized model wraps 6 vision encoder deepstack
        # merger layers as Linear4bit without actual quant_state. BnB asserts
        # on these during forward. Replace them with plain Linear (weights are
        # already float16, no dequantization needed).
        replaced = 0
        for name, module in list(base_model.named_modules()):
            if not isinstance(module, bnb.nn.Linear4bit):
                continue
            if not name.startswith("model.visual"):
                continue
            parts = name.split(".")
            parent = base_model
            for p in parts[:-1]:
                parent = getattr(parent, p)
            w = module.weight.data.to(dtype=torch.bfloat16)
            new_linear = torch.nn.Linear(
                w.shape[1], w.shape[0],
                bias=module.bias is not None,
                device=w.device,
                dtype=torch.bfloat16,
            )
            new_linear.weight = torch.nn.Parameter(w, requires_grad=False)
            if module.bias is not None:
                new_linear.bias = torch.nn.Parameter(
                    module.bias.data.to(dtype=torch.bfloat16), requires_grad=False
                )
            setattr(parent, parts[-1], new_linear)
            replaced += 1
        if replaced:
            logger.info("Replaced %d vision encoder Linear4bit -> Linear", replaced)

        logger.info("Loading LoRA adapter from: %s", adapter_path)
        self.model = PeftModel.from_pretrained(
            base_model,
            str(adapter_path),
            is_trainable=False,
            autocast_adapter_dtype=False,
        )
        self.model.eval()

        self.processor = AutoProcessor.from_pretrained(
            base_model_id,
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

    def run_inference(
        self, pil_image: Image.Image, max_new_tokens: int = 512
    ) -> tuple[dict, str, int]:
        """Run OCR inference on a PIL image.

        Returns:
            (parsed_dict, raw_text, parse_tier)
            parse_tier: 1 = clean JSON, 2 = repaired, 3 = partial regex extraction
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

        generated = output_ids[0][inputs["input_ids"].shape[1]:]
        raw_text = self.processor.decode(generated, skip_special_tokens=True)

        parsed, tier = self._parse_output(raw_text)
        return parsed, raw_text, tier

    def get_vram_info(self) -> tuple[int, int]:
        """Return (used_mb, total_mb) for the model's CUDA device."""
        if not self._loaded or not torch.cuda.is_available():
            return 0, 0
        idx = self.device.index if self.device.index is not None else 0
        used = torch.cuda.memory_allocated(idx) // (1024 * 1024)
        total = torch.cuda.get_device_properties(idx).total_memory // (1024 * 1024)
        return used, total

    def _flush_cuda(self) -> None:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    @staticmethod
    def _parse_output(raw: str) -> tuple[dict, int]:
        """3-tier JSON extraction from model output.

        Tier 1: Clean JSON parse.
        Tier 2: Strip markdown fences, trailing commas, extract JSON
                substring from surrounding text.
        Tier 3: Regex-extract individual fields from malformed output.

        Returns:
            (parsed_dict, tier)
        """
        text = raw.strip()

        # --- Tier 1: clean parse ---
        try:
            return json.loads(text), 1
        except json.JSONDecodeError:
            pass

        # --- Tier 2: repair and retry ---
        repaired = text

        # Strip markdown fences
        if "```" in repaired:
            lines = repaired.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            repaired = "\n".join(lines).strip()

        # Extract first { ... } substring (model may wrap JSON in explanation)
        brace_match = re.search(r"\{[\s\S]*\}", repaired)
        if brace_match:
            repaired = brace_match.group(0)

        # Strip trailing commas before } or ]
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)

        try:
            return json.loads(repaired), 2
        except json.JSONDecodeError:
            pass

        # --- Tier 3: regex field extraction ---
        FIELDS = [
            "date", "patient_name", "philhealth_number",
            "diagnosis_code", "procedure_code", "total_amount",
            "philhealth_benefit", "balance_due",
        ]
        result = {}
        for field in FIELDS:
            # Match "field": "value" or "field": number or "field": null
            pattern = rf'"{field}"\s*:\s*("(?:[^"\\]|\\.)*"|[\d.]+|null)'
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                val = m.group(1)
                if val == "null":
                    result[field] = None
                elif val.startswith('"'):
                    result[field] = val.strip('"')
                else:
                    try:
                        result[field] = float(val)
                    except ValueError:
                        result[field] = val

        if result:
            logger.warning(
                "Tier-3 partial extraction recovered %d/%d fields",
                len(result), len(FIELDS),
            )
            return result, 3

        # Nothing recoverable
        raise ValueError(
            f"Could not extract structured data from model output "
            f"(length={len(text)})"
        )


# Module-level singleton
manager = ModelManager()
