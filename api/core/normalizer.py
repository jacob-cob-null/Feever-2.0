"""Image normalization for Qwen3-VL inference."""

from io import BytesIO

from PIL import Image, UnidentifiedImageError

CANVAS_SIZE = 1024
PAD_COLOR = (245, 245, 245)
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class InvalidImageError(Exception):
    """Raised when an image file is corrupted or unreadable."""
    pass


def validate_image(content_type: str, size: int) -> str | None:
    """Return an error message if the upload is invalid, else None."""
    if content_type not in ALLOWED_TYPES:
        return f"Unsupported image type: {content_type}. Use JPG, PNG, or WebP."
    if size > MAX_FILE_SIZE:
        return f"File too large: {size / 1e6:.1f} MB. Max 10 MB."
    return None


def normalize(image_bytes: bytes) -> Image.Image:
    """Convert raw bytes to a 1024x1024 letterboxed RGB PIL Image.

    Must match training preprocessing exactly to keep mRoPE patch
    grid deterministic and avoid OOM from unexpected token counts.

    Steps:
        1. Open and convert to RGB.
        2. Thumbnail to fit 1024x1024 (LANCZOS, preserves aspect ratio).
        3. Center-paste onto 1024x1024 canvas with pad color (245,245,245).

    No image enhancement (CLAHE, sharpening, deskew) is applied because
    the model was trained on raw letterboxed images. Altering the pixel
    distribution at inference would cause train-test mismatch.

    Raises:
        InvalidImageError: If the image file is corrupted or unreadable.
    """
    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
    except (UnidentifiedImageError, OSError, SyntaxError) as e:
        raise InvalidImageError(
            f"Image file is corrupted or unreadable: {type(e).__name__}"
        ) from e

    img.thumbnail((CANVAS_SIZE, CANVAS_SIZE), Image.LANCZOS)
    canvas = Image.new("RGB", (CANVAS_SIZE, CANVAS_SIZE), PAD_COLOR)
    x = (CANVAS_SIZE - img.width) // 2
    y = (CANVAS_SIZE - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas
