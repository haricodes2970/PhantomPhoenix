"""Optional real-model smoke test.

Run with: pytest tests/test_real_model_smoke.py -v --run-real-model

Requires:
- .venv with torch and transformers installed
- Model weights downloaded (first run downloads ~83 MB)
- GPU or CPU available

This test is SKIPPED by default. Use --run-real-model to enable.
"""

from __future__ import annotations

import io
import os

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.main import app


# Skip by default - requires --run-real-model flag
pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_REAL_MODEL"),
    reason="Set RUN_REAL_MODEL=1 to run real model inference test",
)


def create_test_image_bytes() -> bytes:
    """Create a simple test image."""
    img = Image.new("RGB", (512, 512), (128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.getvalue()


def test_real_model_inference():
    """Run a real inference through the API."""
    client = TestClient(app)
    img_bytes = create_test_image_bytes()

    response = client.post(
        "/api/scans",
        files={"file": ("smoke_test.jpg", img_bytes, "image/jpeg")},
    )

    assert response.status_code == 201
    data = response.json()

    assert "scan_id" in data
    assert data["status"] in ("complete", "failed")

    result = data.get("result")
    if result:
        assert result["input"]["sha256"] is not None
        assert len(result["models"]) == 1
        model = result["models"][0]
        assert model["model_id"] == "buildborderless/CommunityForensics-DeepfakeDet-ViT"
        assert model["status"] in ("ok", "error")

        if model["status"] == "ok":
            assert model["fake_probability"] is not None
            assert 0.0 <= model["fake_probability"] <= 1.0
            assert model["raw_logit"] is not None
            assert model["device"] in ("cuda", "cpu")
            assert model["duration_seconds"] is not None
            assert model["duration_seconds"] > 0

            # Real attention tensors must be derived (eager attention), not faked.
            explainability = result["explainability"]
            assert explainability["status"] == "available"
            assert explainability["kind"] == "attention_rollout"
            metrics = explainability["metrics"]
            assert metrics["num_layers"] > 0
            assert metrics["num_heads"] > 0
            assert metrics["num_patches"] > 0
            for key in ("mean_cls_attention", "max_cls_attention", "attention_entropy"):
                assert isinstance(metrics[key], (int, float))

        assert result["verdict"]["label"] in (
            "LIKELY_AI",
            "LIKELY_REAL",
            "INCONCLUSIVE",
            "ANALYSIS_FAILED",
        )
        assert result["verdict"]["risk"] in ("low", "moderate", "high", "unknown")
        assert len(result["verdict"]["rationale"]) > 0
        assert "calibrated real-world criminal fraud probability" in result["verdict"]["not_claimed"]