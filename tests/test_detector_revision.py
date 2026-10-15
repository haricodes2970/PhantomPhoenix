"""Tests for DetectorAdapter revision configuration and explicit loading error handling."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from backend.detector import DetectorAdapter, DetectorConfig, ModelLoadError


def test_detector_passes_revision_to_pretrained(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that model_revision is passed to both ViTImageProcessor and ViTForImageClassification."""
    DetectorAdapter().reset_for_testing()

    mock_processor_cls = MagicMock()
    mock_model_cls = MagicMock()

    mock_model_instance = MagicMock()
    mock_model_instance.config.num_labels = 1
    mock_processor_instance = MagicMock()
    mock_processor_instance.size = MagicMock(shortest_edge=440)
    mock_processor_instance.crop_size = MagicMock(height=384, shortest_edge=None)

    mock_processor_cls.from_pretrained.return_value = mock_processor_instance
    mock_model_cls.from_pretrained.return_value = mock_model_instance

    monkeypatch.setattr("backend.detector.ViTImageProcessor", mock_processor_cls)
    monkeypatch.setattr("backend.detector.ViTForImageClassification", mock_model_cls)

    config = DetectorConfig(
        model_id="test-model-id",
        model_revision="test-rev-123",
        device="cpu",
    )

    adapter = DetectorAdapter(config=config)
    adapter._load_model()

    mock_processor_cls.from_pretrained.assert_called_once_with(
        "test-model-id", revision="test-rev-123"
    )
    mock_model_cls.from_pretrained.assert_called_once_with(
        "test-model-id", revision="test-rev-123"
    )

    DetectorAdapter().reset_for_testing()


def test_detector_loading_failure_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that loading failures raise ModelLoadError explicitly and store load_error."""
    DetectorAdapter().reset_for_testing()

    mock_processor_cls = MagicMock()
    mock_processor_cls.from_pretrained.side_effect = RuntimeError("Network timeout / Hub unavailable")

    monkeypatch.setattr("backend.detector.ViTImageProcessor", mock_processor_cls)

    config = DetectorConfig(
        model_id="test-model-id",
        model_revision="test-rev-123",
        device="cpu",
    )

    adapter = DetectorAdapter(config=config)
    with pytest.raises(ModelLoadError) as exc_info:
        adapter._load_model()

    assert "Network timeout" in str(exc_info.value)
    assert adapter.health_info()["detector_loaded"] is False
    assert adapter.health_info()["load_error"] is not None

    DetectorAdapter().reset_for_testing()
