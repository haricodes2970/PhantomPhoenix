"""Tests for attribution service."""

from __future__ import annotations

import pytest

from backend.attribution import (
    AttributionService,
    AttributionResult,
    AttributionStatus,
    AttributionMethod,
    CandidateFamily,
    create_unsupported_result,
    create_error_result,
    get_attribution_service,
    reset_attribution_service_for_testing,
)


class TestAttributionSchemas:
    """Test attribution schema validation."""

    def test_candidate_family_valid(self) -> None:
        """Valid candidate family creates successfully."""
        cf = CandidateFamily(
            family="stable-diffusion",
            confidence=0.85,
            evidence_type=AttributionMethod.MODEL_INFERENCE,
            metadata={"variant": "xl"},
        )
        assert cf.family == "stable-diffusion"
        assert cf.confidence == 0.85
        assert cf.evidence_type == AttributionMethod.MODEL_INFERENCE

    def test_candidate_family_confidence_bounds(self) -> None:
        """Confidence must be in [0, 1]."""
        with pytest.raises(ValueError):
            CandidateFamily(family="test", confidence=1.5, evidence_type=AttributionMethod.MODEL_INFERENCE)
        with pytest.raises(ValueError):
            CandidateFamily(family="test", confidence=-0.1, evidence_type=AttributionMethod.MODEL_INFERENCE)

    def test_attribution_result_unsupported(self) -> None:
        """Unsupported result has correct structure."""
        result = create_unsupported_result()
        assert result.status == AttributionStatus.UNSUPPORTED
        assert result.method == AttributionMethod.UNKNOWN
        assert result.candidates == []
        assert len(result.limitations) >= 3
        assert result.error is None

    def test_attribution_result_error(self) -> None:
        """Error result has correct structure."""
        result = create_error_result("Model load failed")
        assert result.status == AttributionStatus.ERROR
        assert result.error == "Model load failed"
        assert "error" in result.limitations[0].lower()


class TestAttributionService:
    """Test attribution service behavior."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        reset_attribution_service_for_testing()

    def test_service_returns_unsupported_by_default(self) -> None:
        """Default service (no model) returns UNSUPPORTED."""
        service = AttributionService()
        result = service.attribute(None)  # image not needed for unsupported path

        assert result.status == AttributionStatus.UNSUPPORTED
        assert result.method == AttributionMethod.UNKNOWN
        assert result.candidates == []
        assert "not available in this deployment" in result.limitations[0]
        assert result.error is None

    def test_service_with_model_id_but_no_load(self) -> None:
        """Service with model_id but no actual model returns UNSUPPORTED."""
        service = AttributionService(model_id="fake/model", model_revision="abc123")
        result = service.attribute(None)

        # Model loading is not implemented, so returns UNSUPPORTED
        assert result.status == AttributionStatus.UNSUPPORTED

    def test_health_info_unsupported(self) -> None:
        """Health info reflects unsupported status."""
        service = AttributionService()
        health = service.health_info()

        assert health["service"] == "attribution"
        assert health["model_id"] is None
        assert health["model_loaded"] is False
        assert health["status"] == "unsupported"
        assert "flux" in health["supported_families"]
        assert "midjourney" in health["supported_families"]

    def test_health_info_with_model_id(self) -> None:
        """Health info shows model_id when configured."""
        service = AttributionService(model_id="test/model", model_revision="rev123")
        health = service.health_info()

        assert health["model_id"] == "test/model"
        assert health["model_revision"] == "rev123"
        assert health["status"] == "unsupported"  # Still unsupported because load not implemented

    def test_singleton_get_attribution_service(self) -> None:
        """get_attribution_service returns singleton."""
        reset_attribution_service_for_testing()
        s1 = get_attribution_service()
        s2 = get_attribution_service()
        assert s1 is s2

    def test_singleton_reset(self) -> None:
        """reset_attribution_service_for_testing creates new instance."""
        reset_attribution_service_for_testing()
        s1 = get_attribution_service()
        reset_attribution_service_for_testing()
        s2 = get_attribution_service()
        assert s1 is not s2