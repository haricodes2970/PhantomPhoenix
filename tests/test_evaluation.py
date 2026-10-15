"""Evaluator tests for the detector evaluation harness."""

from __future__ import annotations

import csv
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from PIL import Image

from backend.evaluation import DetectorEvaluator
from backend.schemas import ModelOutput


def create_synthetic_image(path: Path) -> None:
    """Create a small valid test image."""
    img = Image.new("RGB", (100, 100), (128, 128, 128))
    img.save(path, "JPEG")


def test_evaluator_csv_manifest(tmp_path: Path) -> None:
    """Test evaluation on a CSV manifest with synthetic fixtures."""
    real_img = tmp_path / "real_1.jpg"
    fake_img = tmp_path / "fake_1.jpg"
    create_synthetic_image(real_img)
    create_synthetic_image(fake_img)

    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["path", "label"])
        writer.writerow([str(real_img), "real"])
        writer.writerow([str(fake_img), "fake"])

    # Mock detector returning low prob for real, high prob for fake
    mock_detector = MagicMock()
    def mock_infer(img):
        # We can inspect or return based on call order or just test metrics logic
        pass

    # Let's mock side_effect to return 0.1 for real, 0.9 for fake
    mock_detector.infer.side_effect = [
        ModelOutput(model_id="test", model_revision="v1", role="primary", status="ok", fake_probability=0.05, raw_logit=-3.0, threshold_policy="", limitations=[], device="cpu", duration_seconds=0.01),
        ModelOutput(model_id="test", model_revision="v1", role="primary", status="ok", fake_probability=0.95, raw_logit=3.0, threshold_policy="", limitations=[], device="cpu", duration_seconds=0.01),
    ]

    evaluator = DetectorEvaluator(detector=mock_detector)
    report = evaluator.evaluate_manifest(manifest, threshold=0.5)

    assert report["processed_samples"] == 2
    assert report["metrics"]["accuracy"] == 1.0
    assert report["metrics"]["precision"] == 1.0
    assert report["metrics"]["recall"] == 1.0
    assert report["metrics"]["f1_score"] == 1.0

    # Test export
    json_out, md_out = evaluator.export_summary(report, tmp_path)
    assert json_out.is_file()
    assert md_out.is_file()


def test_evaluator_json_manifest(tmp_path: Path) -> None:
    """Test evaluation on a JSON manifest."""
    img1 = tmp_path / "img1.jpg"
    create_synthetic_image(img1)

    manifest = tmp_path / "manifest.json"
    data = [{"path": str(img1), "label": "real"}]
    with manifest.open("w", encoding="utf-8") as f:
        json.dump(data, f)

    mock_detector = MagicMock()
    mock_detector.infer.return_value = ModelOutput(
        model_id="test", model_revision="v1", role="primary", status="ok",
        fake_probability=0.1, raw_logit=-2.0, threshold_policy="", limitations=[], device="cpu", duration_seconds=0.01
    )

    evaluator = DetectorEvaluator(detector=mock_detector)
    report = evaluator.evaluate_manifest(manifest, threshold=0.5)

    assert report["processed_samples"] == 1
    assert report["metrics"]["accuracy"] == 1.0


def test_evaluator_handles_missing_file(tmp_path: Path) -> None:
    """Test evaluator handles missing image files gracefully in manifest."""
    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["path", "label"])
        writer.writerow(["/nonexistent/path/image.jpg", "real"])

    evaluator = DetectorEvaluator(detector=MagicMock())
    report = evaluator.evaluate_manifest(manifest)

    assert report["processed_samples"] == 0
    assert report["excluded_count"] == 1
    assert report["metrics"] == {}
