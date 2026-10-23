"""Tests for Grad-CAM heatmap generation in detector."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from backend.detector import DetectorAdapter
from backend.detector import get_detector as _get_detector


class TestGradCAMHeatmap:
    """Test Grad-CAM heatmap artifact generation."""

    def setup_method(self) -> None:
        """Reset detector singleton before each test."""
        _get_detector().reset_for_testing()

    def teardown_method(self) -> None:
        """Clean up artifacts after each test."""
        _get_detector().reset_for_testing()
        # Clean up any test artifacts
        artifact_dir = Path("uploads/artifacts")
        if artifact_dir.exists():
            import shutil
            shutil.rmtree(artifact_dir, ignore_errors=True)

    def test_gradcam_artifact_generated(self) -> None:
        """Test that Grad-CAM artifact is generated during inference."""
        detector = DetectorAdapter()
        
        # Create a simple test image
        img = Image.new("RGB", (384, 384), color="red")
        
        # Run inference with scan_id
        scan_id = "test-scan-123"
        result = detector.infer(img, scan_id=scan_id)
        
        # Check explainability includes artifact
        assert result.explainability is not None
        assert result.explainability.get("status") == "available"
        assert result.explainability.get("kind") == "attention_rollout"
        
        artifact_path = result.explainability.get("artifact")
        assert artifact_path is not None, "Grad-CAM artifact should be generated"
        assert artifact_path.endswith("gradcam.jpg")
        
        # Verify file exists
        full_path = Path(artifact_path)
        assert full_path.exists(), f"Artifact file not found: {artifact_path}"
        
        # Verify it's a valid image
        with Image.open(full_path) as artifact_img:
            assert artifact_img.size == img.size
            assert artifact_img.mode == "RGB"

    def test_gradcam_artifact_not_generated_without_scan_id(self) -> None:
        """Test that Grad-CAM artifact is not generated when scan_id is None."""
        detector = DetectorAdapter()
        
        img = Image.new("RGB", (384, 384), color="blue")
        
        # Run inference without scan_id
        result = detector.infer(img, scan_id=None)
        
        artifact_path = result.explainability.get("artifact")
        assert artifact_path is None, "Artifact should not be generated without scan_id"

    def test_gradcam_metrics_computed(self) -> None:
        """Test that attention metrics are computed alongside Grad-CAM."""
        detector = DetectorAdapter()
        
        img = Image.new("RGB", (384, 384), color="green")
        
        result = detector.infer(img, scan_id="test-scan-456")
        
        metrics = result.explainability.get("metrics", {})
        assert "num_layers" in metrics
        assert "num_heads" in metrics
        assert "num_patches" in metrics
        assert "mean_cls_attention" in metrics
        assert "max_cls_attention" in metrics
        assert "attention_entropy" in metrics
        
        # Verify reasonable values
        assert metrics["num_layers"] > 0
        assert metrics["num_heads"] > 0
        assert metrics["num_patches"] > 0
        assert 0 <= metrics["mean_cls_attention"] <= 1
        assert 0 <= metrics["max_cls_attention"] <= 1
        assert metrics["attention_entropy"] >= 0


class TestDetectorExplainabilityLimitations:
    """Test that explainability limitations are properly documented."""

    def setup_method(self) -> None:
        _get_detector().reset_for_testing()

    def teardown_method(self) -> None:
        _get_detector().reset_for_testing()
        import shutil
        shutil.rmtree("uploads/artifacts", ignore_errors=True)

    def test_explainability_limitations_include_gradcam_note(self) -> None:
        """Test that limitations mention Grad-CAM is attention-based, not ground truth."""
        detector = DetectorAdapter()
        
        img = Image.new("RGB", (384, 384), color="yellow")
        result = detector.infer(img, scan_id="test-scan-789")
        
        limitations = result.limitations
        assert any("Grad-CAM" in lim or "attention focus" in lim for lim in limitations), \
            "Limitations should mention Grad-CAM is attention-based"