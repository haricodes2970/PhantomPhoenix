"""Regression tests for ViT attention extraction (XAI) behavior.

Root cause covered here: the default SDPA attention implementation does not
materialize attention matrices, so `output_attentions=True` returns an empty
tuple. The adapter must load with eager attention and must never fabricate
metrics when tensors are missing or invalid.
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest
import torch
from PIL import Image

from backend.detector import DetectorAdapter, DetectorConfig


@pytest.fixture(autouse=True)
def _reset_detector() -> None:
    DetectorAdapter().reset_for_testing()
    yield
    DetectorAdapter().reset_for_testing()


def _uniform_attentions(num_layers: int = 2, num_heads: int = 3, num_patches: int = 16) -> tuple:
    seq = num_patches + 1
    return tuple(torch.ones(1, num_heads, seq, seq) for _ in range(num_layers))


def test_model_loaded_with_eager_attention(monkeypatch: pytest.MonkeyPatch) -> None:
    """Model must request the eager attention implementation during load."""
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

    adapter = DetectorAdapter(
        config=DetectorConfig(model_id="test-model", model_revision="rev", device="cpu")
    )
    adapter._load_model()

    mock_model_cls.from_pretrained.assert_called_once_with(
        "test-model", revision="rev", attn_implementation="eager"
    )


def test_attention_metrics_derived_from_real_tensors() -> None:
    """Uniform attention yields normalized, finite metrics derived from tensors."""
    attentions = _uniform_attentions(num_layers=2, num_heads=3, num_patches=16)
    metrics = DetectorAdapter._compute_attention_metrics(attentions)

    assert metrics != {}
    assert metrics["num_layers"] == 2
    assert metrics["num_heads"] == 3
    assert metrics["num_patches"] == 16
    assert metrics["mean_cls_attention"] == pytest.approx(1 / 16, rel=1e-6)
    assert metrics["max_cls_attention"] == pytest.approx(1 / 16, rel=1e-6)
    assert metrics["attention_entropy"] == pytest.approx(math.log(16), rel=1e-6)
    assert all(math.isfinite(v) for v in metrics.values() if isinstance(v, float))


def test_attention_metrics_empty_tuple_returns_empty() -> None:
    """SDPA produces an empty tuple; no metrics must be fabricated."""
    assert DetectorAdapter._compute_attention_metrics(()) == {}


def test_attention_metrics_none_returns_empty() -> None:
    assert DetectorAdapter._compute_attention_metrics(None) == {}


def test_attention_metrics_non_finite_returns_empty() -> None:
    seq = 17
    tensor = torch.ones(1, 2, seq, seq)
    tensor[0, 0, 0, 1] = float("nan")
    assert DetectorAdapter._compute_attention_metrics((tensor,)) == {}


def test_attention_metrics_zero_sum_returns_empty() -> None:
    seq = 17
    tensor = torch.zeros(1, 2, seq, seq)
    assert DetectorAdapter._compute_attention_metrics((tensor,)) == {}


def test_attention_metrics_invalid_shape_returns_empty() -> None:
    assert DetectorAdapter._compute_attention_metrics((torch.ones(1, 2, 17),)) == {}


def test_attention_metrics_no_patches_returns_empty() -> None:
    assert DetectorAdapter._compute_attention_metrics((torch.ones(1, 2, 1, 1),)) == {}


class _FakeOutput:
    def __init__(self, logits: torch.Tensor, attentions: object) -> None:
        self.logits = logits
        self.attentions = attentions


class _FakeModel:
    name_or_path = "test-model"

    def __init__(self, attentions: object, logit: float = 0.0) -> None:
        self._attentions = attentions
        self._logit = logit

    def to(self, device: object) -> "_FakeModel":
        return self

    def eval(self) -> "_FakeModel":
        return self

    def __call__(self, **kwargs: object) -> _FakeOutput:
        assert kwargs.get("output_attentions") is True
        return _FakeOutput(torch.tensor([[self._logit]]), self._attentions)


class _FakeProcessor:
    def __call__(self, images: object = None, return_tensors: str | None = None) -> dict:
        return {"pixel_values": torch.zeros(1, 3, 384, 384)}


def _adapter_with(attentions: object) -> DetectorAdapter:
    adapter = DetectorAdapter(
        config=DetectorConfig(model_id="test-model", model_revision="rev", device="cpu")
    )
    adapter._processor = _FakeProcessor()
    adapter._model = _FakeModel(attentions)  # type: ignore[assignment]
    return adapter


def test_run_inference_unavailable_without_attention_tensors() -> None:
    """Empty attention output must be reported as unavailable, not fabricated."""
    adapter = _adapter_with(())
    output = adapter._run_inference("cpu", Image.new("RGB", (8, 8)))

    assert output.status == "ok"
    assert output.fake_probability == pytest.approx(0.5)
    assert output.explainability is not None
    assert output.explainability["status"] == "unavailable"
    assert output.explainability["metrics"] == {}


def test_run_inference_available_with_attention_tensors() -> None:
    """Valid attention tensors must yield available, finite metrics."""
    adapter = _adapter_with(_uniform_attentions(num_layers=2, num_heads=3, num_patches=16))
    output = adapter._run_inference("cpu", Image.new("RGB", (8, 8)))

    assert output.explainability is not None
    assert output.explainability["status"] == "available"
    assert output.explainability["kind"] == "attention_rollout"
    metrics = output.explainability["metrics"]
    assert metrics["num_patches"] == 16
    assert math.isfinite(metrics["attention_entropy"])
