"""Custom exception hierarchy for structured error handling."""


class FeeverError(Exception):
    """Base exception for all Fee-Ver application errors."""

    status_code: int = 500
    error_type: str = "internal_error"

    def __init__(self, detail: str = "An unexpected error occurred"):
        self.detail = detail
        super().__init__(detail)


class InvalidImageError(FeeverError):
    """Image is corrupted, unreadable, or fails validation."""

    status_code = 400
    error_type = "invalid_image"


class ExtractionError(FeeverError):
    """Model output could not be parsed into structured data (all tiers failed)."""

    status_code = 422
    error_type = "extraction_failed"


class InferenceTimeoutError(FeeverError):
    """Inference exceeded the time budget."""

    status_code = 504
    error_type = "inference_timeout"


class InferenceBusyError(FeeverError):
    """Inference lock is held by another request."""

    status_code = 503
    error_type = "busy"

    def __init__(self):
        super().__init__("Inference engine busy. Try again shortly.")


class ModelNotReadyError(FeeverError):
    """Model is still loading or failed to load."""

    status_code = 503
    error_type = "not_ready"

    def __init__(self):
        super().__init__("Model is still loading. Try again in a moment.")
