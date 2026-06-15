"""AES-256-GCM encryption helpers for RA 10173 compliance."""

import base64
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_BYTES = 12


def load_key(secret: str) -> bytes:
    """Decode a base64-encoded 32-byte AES key.

    Raises ValueError if the key is not exactly 32 bytes after decoding.
    """
    raw = base64.b64decode(secret)
    if len(raw) != 32:
        raise ValueError(
            f"AES key must be 32 bytes, got {len(raw)}. "
            "Generate with: python -c \"import os,base64; print(base64.b64encode(os.urandom(32)).decode())\""
        )
    return raw


def encrypt(data: bytes, key: bytes) -> bytes:
    """Encrypt data with AES-256-GCM.

    Returns nonce (12 bytes) || ciphertext+tag.
    """
    nonce = os.urandom(NONCE_BYTES)
    ct = AESGCM(key).encrypt(nonce, data, None)
    return nonce + ct


def decrypt(blob: bytes, key: bytes) -> bytes:
    """Decrypt a nonce || ciphertext+tag blob."""
    nonce = blob[:NONCE_BYTES]
    ct = blob[NONCE_BYTES:]
    return AESGCM(key).decrypt(nonce, ct, None)


def encrypt_and_save(
    payload: dict,
    image_bytes: bytes,
    key: bytes,
    out_dir: Path,
    request_id: str,
) -> None:
    """Encrypt JSON payload + image and write to disk.

    Files written:
        {out_dir}/{request_id}_payload.enc
        {out_dir}/{request_id}_image.enc
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    (out_dir / f"{request_id}_payload.enc").write_bytes(
        encrypt(payload_bytes, key)
    )
    (out_dir / f"{request_id}_image.enc").write_bytes(
        encrypt(image_bytes, key)
    )


def generate_key() -> str:
    """Generate a random base64-encoded 32-byte key for .env."""
    return base64.b64encode(os.urandom(32)).decode()
