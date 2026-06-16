"""Tests for image normalization and validation."""

import pytest

from api.core.normalizer import (
    CANVAS_SIZE,
    InvalidImageError,
    normalize,
    validate_image,
)


class TestValidateImage:
    def test_valid_jpeg(self):
        assert validate_image("image/jpeg", 1_000_000) is None

    def test_valid_png(self):
        assert validate_image("image/png", 500_000) is None

    def test_valid_webp(self):
        assert validate_image("image/webp", 500_000) is None

    def test_invalid_type(self):
        error = validate_image("application/pdf", 500_000)
        assert error is not None
        assert "Unsupported" in error

    def test_too_large(self):
        error = validate_image("image/png", 15_000_000)
        assert error is not None
        assert "too large" in error.lower()

    def test_exactly_max_size(self):
        assert validate_image("image/png", 10 * 1024 * 1024) is None

    def test_one_byte_over(self):
        error = validate_image("image/png", 10 * 1024 * 1024 + 1)
        assert error is not None


class TestNormalize:
    def test_valid_image_returns_correct_size(self, valid_png_bytes):
        result = normalize(valid_png_bytes)
        assert result.size == (CANVAS_SIZE, CANVAS_SIZE)
        assert result.mode == "RGB"

    def test_landscape_image_letterboxed(self):
        """Wide image should be letterboxed (padded top and bottom)."""
        from PIL import Image
        from io import BytesIO
        buf = BytesIO()
        Image.new("RGB", (800, 200), (0, 0, 0)).save(buf, format="PNG")
        result = normalize(buf.getvalue())
        assert result.size == (CANVAS_SIZE, CANVAS_SIZE)

    def test_portrait_image_letterboxed(self):
        """Tall image should be letterboxed (padded left and right)."""
        from PIL import Image
        from io import BytesIO
        buf = BytesIO()
        Image.new("RGB", (200, 800), (0, 0, 0)).save(buf, format="PNG")
        result = normalize(buf.getvalue())
        assert result.size == (CANVAS_SIZE, CANVAS_SIZE)

    def test_corrupted_bytes_raises(self, corrupted_bytes):
        with pytest.raises(InvalidImageError, match="corrupted"):
            normalize(corrupted_bytes)

    def test_empty_bytes_raises(self):
        with pytest.raises(InvalidImageError):
            normalize(b"")

    def test_truncated_png_raises(self):
        # First few bytes of a PNG header, then garbage
        truncated = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
        with pytest.raises(InvalidImageError):
            normalize(truncated)
