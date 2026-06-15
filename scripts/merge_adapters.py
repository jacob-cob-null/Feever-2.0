"""Prepare the composed 97:3 LoRA adapter for inference.

Runtime strategy: load the 4-bit BnB base model (~2.5 GB VRAM)
+ this LoRA adapter (~253 MB) = ~3 GB total.  Fits in 8 GB VRAM.

If a pre-composed adapter exists (recovered / from compose_adapters.py),
copies it with the correct config into models/merged/qwen3vl_merged/.

If no composed adapter exists, performs the 97:3 interpolation from the
logic and noise adapter state_dicts on CPU (< 1 GB RAM).
"""

import json
import shutil
import struct
import sys
from pathlib import Path

try:
    from safetensors.torch import load_file, save_file
    HAS_TORCH = True
except (ImportError, OSError):
    HAS_TORCH = False

ROOT = Path(__file__).resolve().parent.parent
ADAPTER_DIR = ROOT / "models" / "reserved" / "adapters"
LOGIC_DIR = ADAPTER_DIR / "logic"
NOISE_DIR = ADAPTER_DIR / "noise"
COMPOSED_DIR = ADAPTER_DIR / "composed"
MERGED_DIR = ROOT / "models" / "merged" / "qwen3vl_merged"

LOGIC_WEIGHT = 0.97
NOISE_WEIGHT = 0.03


def _read_safetensors_header(path: Path) -> dict:
    """Read safetensors metadata header without loading tensors."""
    with open(path, "rb") as f:
        header_size = struct.unpack("<Q", f.read(8))[0]
        header = json.loads(f.read(header_size))
    # Remove __metadata__ key if present
    header.pop("__metadata__", None)
    return header


def compose_from_adapters():
    """Compose logic + noise adapters at 97:3 on CPU.

    Requires torch (run in conda paige env if needed).
    """
    if not HAS_TORCH:
        print("ERROR: torch required for composition but not available.")
        print("  Run this in the 'paige' conda env, or provide a")
        print("  pre-composed adapter in models/reserved/adapters/composed/")
        sys.exit(1)

    print("Composing adapters (97:3 linear interpolation on CPU)...")

    logic_w = load_file(str(LOGIC_DIR / "adapter_model.safetensors"),
                        device="cpu")
    noise_w = load_file(str(NOISE_DIR / "adapter_model.safetensors"),
                        device="cpu")

    composed = {}
    for key, tensor in logic_w.items():
        if key in noise_w:
            composed[key] = LOGIC_WEIGHT * tensor + NOISE_WEIGHT * noise_w[key]
        else:
            composed[key] = tensor

    for key, tensor in noise_w.items():
        if key not in logic_w:
            composed[key] = NOISE_WEIGHT * tensor

    COMPOSED_DIR.mkdir(parents=True, exist_ok=True)
    save_file(composed, str(COMPOSED_DIR / "adapter_model.safetensors"))

    print(f"  Logic keys: {len(logic_w)}, Noise keys: {len(noise_w)}")
    print(f"  Composed keys: {len(composed)}")
    del logic_w, noise_w, composed


def main():
    logic_st = LOGIC_DIR / "adapter_model.safetensors"
    logic_cfg = LOGIC_DIR / "adapter_config.json"
    composed_st = COMPOSED_DIR / "adapter_model.safetensors"

    if not logic_st.exists() or not logic_cfg.exists():
        print(f"ERROR: Logic adapter not found at {LOGIC_DIR}")
        sys.exit(1)

    # --- Ensure composed adapter exists ---
    if composed_st.exists():
        size_mb = composed_st.stat().st_size / 1e6
        print(f"Found pre-composed adapter ({size_mb:.1f} MB)")
    else:
        if not (NOISE_DIR / "adapter_model.safetensors").exists():
            print("ERROR: No composed adapter and noise adapter missing")
            sys.exit(1)
        compose_from_adapters()

    # --- Ensure composed dir has adapter_config.json ---
    if not (COMPOSED_DIR / "adapter_config.json").exists():
        shutil.copy2(logic_cfg, COMPOSED_DIR / "adapter_config.json")
        print("Copied adapter_config.json from logic adapter")

    # --- Assemble merged output ---
    MERGED_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nAssembling {MERGED_DIR.relative_to(ROOT)}/")

    shutil.copy2(composed_st, MERGED_DIR / "adapter_model.safetensors")
    for name in ("adapter_config.json", "tokenizer.json",
                 "tokenizer_config.json", "processor_config.json",
                 "chat_template.jinja"):
        src = LOGIC_DIR / name
        if src.exists():
            shutil.copy2(src, MERGED_DIR / name)

    # --- Validate (header-only, no torch needed) ---
    header = _read_safetensors_header(MERGED_DIR / "adapter_model.safetensors")
    num_tensors = len(header)

    with open(MERGED_DIR / "adapter_config.json") as f:
        cfg = json.load(f)

    adapter_mb = (MERGED_DIR / "adapter_model.safetensors").stat().st_size / 1e6
    print(f"  adapter_model.safetensors : {adapter_mb:.1f} MB ({num_tensors} tensors)")
    print(f"  r={cfg['r']}, alpha={cfg['lora_alpha']}, type={cfg['peft_type']}")
    print(f"  Base: {cfg['base_model_name_or_path']}")
    print(f"\nRuntime VRAM estimate:")
    print(f"  Base model (q4 BnB) : ~2.5 GB")
    print(f"  LoRA adapter        : ~{adapter_mb / 1e3:.2f} GB")
    print(f"  KV cache + overhead : ~1.5 GB")
    print(f"  Total               : ~4.3 GB  (fits 8 GB)")


if __name__ == "__main__":
    main()
