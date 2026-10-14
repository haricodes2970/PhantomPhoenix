"""Tests for verdict policy."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.schemas import VerdictLabel, RiskLevel


def test_likely_ai_verdict(client: TestClient, mock_detector_high_score) -> None:
    """High fake probability -> LIKELY_AI."""
    import io
    from PIL import Image
    img = Image.new("RGB", (100, 100), (128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    response = client.post(
        "/api/scans",
        files={"file": ("test.jpg", img_bytes, "image/jpeg")},
    )

    assert response.status_code == 201
    data = response.json()
    result = data["result"]

    assert result["verdict"]["label"] == VerdictLabel.LIKELY_AI
    assert result["verdict"]["risk"] == RiskLevel.HIGH
    assert any("LIKELY_AI" in r and "0.95" in r for r in result["verdict"]["rationale"])
    assert "generator identity" in result["verdict"]["not_claimed"]
    assert "calibrated real-world criminal fraud probability" in result["verdict"]["not_claimed"]


def test_likely_real_verdict(client: TestClient, mock_detector) -> None:
    """Low fake probability -> LIKELY_REAL."""
    import io
    from PIL import Image
    img = Image.new("RGB", (100, 100), (128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    response = client.post(
        "/api/scans",
        files={"file": ("test.jpg", img_bytes, "image/jpeg")},
    )

    assert response.status_code == 201
    data = response.json()
    result = data["result"]

    assert result["verdict"]["label"] == VerdictLabel.LIKELY_REAL
    assert result["verdict"]["risk"] == RiskLevel.LOW
    assert any("LIKELY_REAL" in r and "0.10" in r for r in result["verdict"]["rationale"])
    assert "generator identity" in result["verdict"]["not_claimed"]
    assert "calibrated real-world criminal fraud probability" in result["verdict"]["not_claimed"]


def test_inconclusive_verdict(client: TestClient, mock_detector_mid_score) -> None:
    """Mid-range fake probability -> INCONCLUSIVE."""
    import io
    from PIL import Image
    img = Image.new("RGB", (100, 100), (128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    response = client.post(
        "/api/scans",
        files={"file": ("test.jpg", img_bytes, "image/jpeg")},
    )

    assert response.status_code == 201
    data = response.json()
    result = data["result"]

    assert result["verdict"]["label"] == VerdictLabel.INCONCLUSIVE
    assert result["verdict"]["risk"] == RiskLevel.MODERATE
    assert any("INCONCLUSIVE" in r and "0.50" in r for r in result["verdict"]["rationale"])


def test_detector_error_never_produces_likely_real(client: TestClient, mock_detector_error) -> None:
    """Detector errors must result in ANALYSIS_FAILED, never LIKELY_REAL."""
    import io
    from PIL import Image
    img = Image.new("RGB", (100, 100), (128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    response = client.post(
        "/api/scans",
        files={"file": ("test.jpg", img_bytes, "image/jpeg")},
    )

    assert response.status_code == 201
    data = response.json()
    result = data["result"]

    assert result["verdict"]["label"] == VerdictLabel.ANALYSIS_FAILED
    assert result["verdict"]["risk"] == RiskLevel.UNKNOWN
    assert result["status"] == "failed"
    assert result["error"] is not None
    # Verify it's not LIKELY_REAL
    assert result["verdict"]["label"] != VerdictLabel.LIKELY_REAL