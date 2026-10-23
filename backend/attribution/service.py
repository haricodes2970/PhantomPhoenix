"""Generator and editing attribution service.

This module provides the attribution service interface. In the current deployment,
no defensible attribution model is available, so the service returns UNSUPPORTED
with explicit limitations. This is intentional and honest behavior.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.attribution.schemas import (
    AttributionResult,
    AttributionStatus,
    AttributionMethod,
    CandidateFamily,
    create_unsupported_result,
    create_error_result,
)

logger = logging.getLogger(__name__)


class AttributionService:
    """
    Generator and editing attribution service.

    Design principles:
    - Never fabricate generator identities.
    - Return UNSUPPORTED when no model is available (not ERROR).
    - Distinguish model inference from verified provenance.
    - Confidence is NOT calibrated probability without calibration.
    """

    def __init__(
        self,
        model_id: str | None = None,
        model_revision: str | None = None,
        device: str = "auto",
    ) -> None:
        self._model_id = model_id
        self._model_revision = model_revision
        self._device = device
        self._model = None
        self._load_error: str | None = None

        # Supported families (for documentation; not inferred without model)
        self._supported_families = [
            "stable-diffusion",
            "flux",
            "midjourney",
            "dalle",
            "gan",
            "photoshop-generative",
            "unknown",
        ]

    def _load_model(self) -> bool:
        """Load attribution model. Returns True if successful."""
        # PLACEHOLDER: No attribution model is currently licensed/available.
        # When a model becomes available, implement loading here.
        # Example structure:
        # try:
        #     from transformers import AutoModelForImageClassification, AutoImageProcessor
        #     self._processor = AutoImageProcessor.from_pretrained(self._model_id, revision=self._model_revision)
        #     self._model = AutoModelForImageClassification.from_pretrained(...)
        #     return True
        # except Exception as exc:
        #     self._load_error = str(exc)
        #     logger.warning("Attribution model load failed: %s", exc)
        #     return False
        # Model loading not implemented - indicate this is a placeholder deployment
        self._load_error = "Attribution model loading not implemented in this deployment"
        return False

    def attribute(self, image: Any) -> AttributionResult:
        """
        Run generator/editing attribution on an image.

        Args:
            image: PIL Image or compatible input

        Returns:
            AttributionResult with status, candidates, and limitations.
        """
        # If no model configured, return UNSUPPORTED immediately
        if self._model_id is None:
            return create_unsupported_result()

        # Try to load model if not already loaded
        if self._model is None and self._load_error is None:
            self._load_model()

        # If model loading is not implemented (placeholder deployment), return UNSUPPORTED
        if self._load_error and "not implemented" in self._load_error:
            return create_unsupported_result()

        # If model failed to load for other reasons, return error
        if self._load_error:
            return create_error_result(self._load_error)

        # PLACEHOLDER: Actual inference would go here when model is available
        # try:
        #     inputs = self._processor(images=image, return_tensors="pt")
        #     inputs = {k: v.to(self._device) for k, v in inputs.items()}
        #     with torch.inference_mode():
        #         outputs = self._model(**inputs)
        #     logits = outputs.logits
        #     probs = torch.softmax(logits, dim=-1)
        #     # Map to candidate families...
        #     return AttributionResult(...)
        # except Exception as exc:
        #     return create_error_result(str(exc))

        # Model loaded but inference not implemented
        return create_unsupported_result()

    def health_info(self) -> dict[str, Any]:
        """Return service health information."""
        if self._model_id is None:
            status = "unsupported"
        elif self._load_error and "not implemented" in self._load_error:
            status = "unsupported"
        elif self._load_error:
            status = "error"
        elif self._model is not None:
            status = "ready"
        else:
            status = "unsupported"

        return {
            "service": "attribution",
            "model_id": self._model_id,
            "model_revision": self._model_revision,
            "model_loaded": self._model is not None,
            "load_error": self._load_error,
            "supported_families": self._supported_families,
            "status": status,
        }


# Singleton instance (like DetectorAdapter)
_attribution_service: AttributionService | None = None


def get_attribution_service() -> AttributionService:
    """Get or create the singleton attribution service."""
    global _attribution_service
    if _attribution_service is None:
        _attribution_service = AttributionService()
    return _attribution_service


def reset_attribution_service_for_testing() -> None:
    """Reset singleton for testing. Only use in tests."""
    global _attribution_service
    _attribution_service = None