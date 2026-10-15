"""Detector adapter - encapsulates model loading and inference."""

from __future__ import annotations

import hashlib
import time
import threading
from dataclasses import dataclass
from typing import Any

import torch
from PIL import Image
from transformers import ViTForImageClassification, ViTImageProcessor

from backend.config import settings
from backend.schemas import ModelOutput


@dataclass(frozen=True)
class DetectorConfig:
    """Immutable detector configuration."""

    model_id: str
    model_revision: str = "ac6ee457bea904a373065754107451793b56db00"
    device: str = "auto"  # auto, cuda, cpu
    expected_num_labels: int = 1
    expected_shortest_edge: int = 440
    expected_crop: int = 384


class DetectorError(Exception):
    """Detector-specific error."""

    pass


class ModelLoadError(DetectorError):
    """Failed to load model weights or config."""

    pass


class InferenceError(DetectorError):
    """Inference failed on all attempted devices."""

    pass


class ConfigMismatchError(DetectorError):
    """Loaded model doesn't match expected config."""

    pass


class DetectorAdapter:
    """Thread-safe detector adapter that loads model once per process."""

    _instance: DetectorAdapter | None = None
    _lock = threading.Lock()

    def __new__(cls, config: DetectorConfig | None = None) -> DetectorAdapter:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: DetectorConfig | None = None) -> None:
        if self._initialized:
            return
        self._config = config or DetectorConfig(
            model_id=settings.model_id,
            model_revision=settings.model_revision,
            device=settings.device,
        )
        self._model: ViTForImageClassification | None = None
        self._processor: ViTImageProcessor | None = None
        self._device: torch.device | None = None
        self._load_error: str | None = None
        self._initialized = True

    def _load_model(self) -> None:
        """Load model and processor. Called once on first inference."""
        if self._model is not None or self._load_error is not None:
            return

        try:
            self._processor = ViTImageProcessor.from_pretrained(
                self._config.model_id, revision=self._config.model_revision
            )
            self._model = ViTForImageClassification.from_pretrained(
                self._config.model_id, revision=self._config.model_revision
            )
        except Exception as exc:
            self._load_error = f"{type(exc).__name__}: {exc}"
            raise ModelLoadError(self._load_error) from exc

        # Validate config matches documented semantics
        cfg = self._model.config
        size = getattr(self._processor, "size", None)
        crop = getattr(self._processor, "crop_size", None)
        shortest = getattr(size, "shortest_edge", None)
        crop_edge = getattr(crop, "height", None) or getattr(crop, "shortest_edge", None)
        num_labels = int(getattr(cfg, "num_labels", -1))

        if not (
            num_labels == self._config.expected_num_labels
            and shortest == self._config.expected_shortest_edge
            and crop_edge == self._config.expected_crop
        ):
            self._load_error = (
                f"Config mismatch: expected num_labels={self._config.expected_num_labels}, "
                f"shortest_edge={self._config.expected_shortest_edge}, "
                f"crop={self._config.expected_crop}; "
                f"got num_labels={num_labels}, shortest_edge={shortest}, crop={crop_edge}"
            )
            raise ConfigMismatchError(self._load_error)

    def _select_device(self) -> list[str]:
        """Return ordered list of devices to try."""
        if self._config.device == "cpu":
            return ["cpu"]
        if self._config.device == "cuda":
            return ["cuda"]
        # auto
        return ["cuda", "cpu"] if torch.cuda.is_available() else ["cpu"]

    def _run_inference(self, device_name: str, pixels: Image.Image) -> ModelOutput:
        """Run inference on a specific device."""
        device = torch.device(device_name)
        self._model.to(device)
        self._model.eval()

        inputs = self._processor(images=pixels, return_tensors="pt")
        inputs = {key: value.to(device) for key, value in inputs.items()}

        if device.type == "cuda":
            torch.cuda.synchronize()
        started = time.perf_counter()
        with torch.inference_mode():
            logits = self._model(**inputs).logits
        if device.type == "cuda":
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - started

        logit = float(logits.detach().float().cpu().reshape(-1)[0])
        fake_probability = float(torch.sigmoid(torch.tensor(logit)))

        return ModelOutput(
            model_id=self._config.model_id,
            model_revision=str(getattr(self._model, "name_or_path", self._config.model_id)),
            role="primary",
            status="ok",
            fake_probability=fake_probability,
            raw_logit=logit,
            threshold_policy="0.80 likely_ai / 0.20 likely_real",
            limitations=[
                "Not calibrated on images from this deployment",
                "Training data may not cover recent generators",
                "Single-model screening aid only",
            ],
            device=device_name,
            duration_seconds=round(elapsed, 6),
        )

    def infer(self, image: Image.Image) -> ModelOutput:
        """Run inference with device fallback. Raises InferenceError if all fail."""
        self._load_model()

        if self._load_error:
            raise InferenceError(f"Model not loaded: {self._load_error}")

        errors: list[str] = []
        for device_name in self._select_device():
            if device_name == "cuda" and not torch.cuda.is_available():
                errors.append("cuda requested but torch.cuda.is_available() is false")
                continue
            try:
                return self._run_inference(device_name, image)
            except Exception as exc:
                errors.append(f"{device_name}: {type(exc).__name__}: {exc}")

        raise InferenceError(f"Inference failed on all devices: {'; '.join(errors)}")

    def health_info(self) -> dict[str, Any]:
        """Return health information for the /health endpoint."""
        cuda_available = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if cuda_available else None
        # Model loads lazily on first inference. Consider "configured" as healthy
        # if no load error has occurred.
        detector_ready = self._load_error is None
        return {
            "detector_loaded": self._model is not None and self._load_error is None,
            "detector_configured": detector_ready,
            "detector_model_id": self._config.model_id,
            "cuda_available": cuda_available,
            "gpu_name": gpu_name,
            "load_error": self._load_error,
        }

    def reset_for_testing(self) -> None:
        """Reset singleton state for testing. Only use in tests."""
        with self._lock:
            DetectorAdapter._instance = None
            self._model = None
            self._processor = None
            self._device = None
            self._load_error = None
            self._initialized = False


def get_detector() -> DetectorAdapter:
    """Dependency injection helper for FastAPI."""
    return DetectorAdapter()