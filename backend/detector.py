"""Detector adapter - encapsulates model loading and inference."""

from __future__ import annotations

import hashlib
import logging
import math
import os
import time
import threading
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
from PIL import Image, ImageFilter
from transformers import ViTForImageClassification, ViTImageProcessor

from backend.config import settings
from backend.schemas import ModelOutput

logger = logging.getLogger(__name__)


ARTIFACT_BASE_DIR = "uploads/artifacts"


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
            # "eager" attention is required: the default SDPA kernel does not
            # materialize attention matrices, so output_attentions=True would
            # return an empty tuple and no genuine explainability could be derived.
            self._model = ViTForImageClassification.from_pretrained(
                self._config.model_id,
                revision=self._config.model_revision,
                attn_implementation="eager",
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

    def _run_inference(self, device_name: str, pixels: Image.Image, scan_id: str | None = None) -> ModelOutput:
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
            outputs = self._model(**inputs, output_attentions=True)
            logits = outputs.logits
            attentions = getattr(outputs, "attentions", None)
        if device.type == "cuda":
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - started

        logit = float(logits.detach().float().cpu().reshape(-1)[0])
        fake_probability = float(torch.sigmoid(torch.tensor(logit)))

        attn_metrics = self._compute_attention_metrics(attentions)

        # Compute Grad-CAM heatmap artifact
        gradcam_artifact = None
        if scan_id and attentions is not None:
            gradcam_artifact = self._compute_gradcam_heatmap(attentions, pixels.size, scan_id)

        explainability_data = {
            "status": "available" if attn_metrics else "unavailable",
            "kind": "attention_rollout",
            "artifact": gradcam_artifact,
            "metrics": attn_metrics,
        }

        return ModelOutput(
            model_id=self._config.model_id,
            model_revision=str(getattr(self._model, "name_or_path", self._config.model_id)),
            role="primary",
            status="ok",
            fake_probability=fake_probability,
            raw_logit=logit,
            threshold_policy=f"{settings.likely_ai_threshold:.2f} likely_ai / {settings.likely_real_threshold:.2f} likely_real",
            limitations=[
                "Not calibrated on images from this deployment",
                "Training data may not cover recent generators",
                "Single-model screening aid only",
                "Grad-CAM heatmap shows attention focus, not ground-truth localization",
            ],
            device=device_name,
            duration_seconds=round(elapsed, 6),
            explainability=explainability_data,
        )

    @staticmethod
    def _compute_attention_metrics(attentions: Any) -> dict[str, Any]:
        """Derive a CLS-to-patch attention summary from real attention tensors.

        Returns an empty dict when attention tensors are unavailable, empty, or
        contain non-finite values. This never substitutes fabricated metrics: the
        caller reports explainability as "unavailable" when no valid tensors exist.
        """
        if attentions is None:
            return {}
        try:
            if len(attentions) == 0:  # SDPA path returns an empty tuple
                return {}

            last_layer = attentions[-1].detach().float().cpu()
            if last_layer.dim() != 4:
                return {}

            num_layers = len(attentions)
            num_heads = int(last_layer.shape[1])
            mean_heads = last_layer.mean(dim=1)[0]  # [seq_len, seq_len]
            num_patches = int(mean_heads.shape[-1]) - 1
            if num_patches <= 0:
                return {}

            cls_to_patches = mean_heads[0, 1:]  # attention from [CLS] to image patches
            if not bool(torch.isfinite(cls_to_patches).all()):
                return {}

            total = cls_to_patches.sum()
            if not bool(torch.isfinite(total)) or float(total) <= 0.0:
                return {}

            probs = cls_to_patches / (total + 1e-12)
            entropy = float(-(probs * torch.log(probs + 1e-12)).sum())

            metrics: dict[str, Any] = {
                "num_layers": num_layers,
                "num_heads": num_heads,
                "num_patches": num_patches,
                "mean_cls_attention": float(probs.mean()),
                "max_cls_attention": float(probs.max()),
                "attention_entropy": entropy,
            }
            numeric = [v for v in metrics.values() if isinstance(v, float)]
            if not all(math.isfinite(v) for v in numeric):
                return {}
            return metrics
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to derive attention metrics: %s", exc)
            return {}

    def _compute_gradcam_heatmap(
        self, attentions: Any, image_size: tuple[int, int], scan_id: str
    ) -> str | None:
        """
        Compute Grad-CAM style heatmap from ViT attention and save as artifact.

        Uses attention rollout: mean attention from [CLS] token to patches across heads
        in the last layer, reshaped to spatial grid and upsampled to image resolution.

        Returns:
            Relative path to saved heatmap artifact, or None if computation fails.
        """
        if attentions is None:
            return None
        try:
            if len(attentions) == 0:
                return None

            last_layer = attentions[-1].detach().float().cpu()
            if last_layer.dim() != 4:
                return None

            # Mean across heads: [seq_len, seq_len]
            mean_heads = last_layer.mean(dim=1)[0]
            num_patches = int(mean_heads.shape[-1]) - 1
            if num_patches <= 0:
                return None

            # CLS-to-patch attention (excluding CLS-to-CLS)
            cls_to_patches = mean_heads[0, 1:]
            if not bool(torch.isfinite(cls_to_patches).all()):
                return None

            total = cls_to_patches.sum()
            if not bool(torch.isfinite(total)) or float(total) <= 0.0:
                return None

            # Normalize to probability distribution over patches
            patch_attention = cls_to_patches / (total + 1e-12)

            # Reshape to spatial grid (assuming square patch grid)
            grid_size = int(math.sqrt(num_patches))
            if grid_size * grid_size != num_patches:
                # Non-square grid (unlikely for ViT) - fallback to 1D
                attention_map = patch_attention.numpy().reshape(1, num_patches)
            else:
                attention_map = patch_attention.numpy().reshape(grid_size, grid_size)

            # Upsample to image resolution using PIL
            attention_img = Image.fromarray((attention_map * 255).astype(np.uint8), mode="L")
            attention_img = attention_img.resize(image_size, Image.Resampling.BICUBIC)

            # Apply colormap (jet-like heatmap)
            # Convert to RGB heatmap: blue->cyan->green->yellow->red
            heatmap_arr = np.array(attention_img, dtype=np.float32) / 255.0
            # Simple jet colormap approximation
            r = np.clip(1.5 - abs(4 * heatmap_arr - 3), 0, 1)
            g = np.clip(1.5 - abs(4 * heatmap_arr - 2), 0, 1)
            b = np.clip(1.5 - abs(4 * heatmap_arr - 1), 0, 1)
            heatmap_rgb = np.stack([r, g, b], axis=-1)
            heatmap_img = Image.fromarray((heatmap_rgb * 255).astype(np.uint8))

            # Blend with original image for context (50% opacity)
            # Note: We don't have the original image here, so save heatmap alone
            # The report can overlay it if needed

            # Save artifact
            artifact_dir = os.path.join(ARTIFACT_BASE_DIR, scan_id)
            os.makedirs(artifact_dir, exist_ok=True)
            artifact_path = os.path.join(artifact_dir, "gradcam.jpg")
            heatmap_img.save(artifact_path, "JPEG", quality=90)

            return os.path.relpath(artifact_path, start=".")

        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to compute Grad-CAM heatmap: %s", exc)
            return None

    def infer(self, image: Image.Image, scan_id: str | None = None) -> ModelOutput:
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
                return self._run_inference(device_name, image, scan_id)
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