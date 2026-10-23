"""Real end-to-end integration regression test for PHANTOM PHOENIX."""

from __future__ import annotations

import io
import os
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import delete

from backend.database import sync_session_factory
from backend.main import app, get_detector_dependency
from backend.models import Scan
from backend.schemas import ModelOutput

# Skip DB-backed E2E tests unless RUN_DB_TESTS=1
pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_DB_TESTS"),
    reason="Set RUN_DB_TESTS=1 to run database-backed end-to-end integration tests",
)


def create_test_image_bytes() -> bytes:
    """Create a sample test JPEG image."""
    img = Image.new("RGB", (256, 256), (200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client with mocked detector for reliable deterministic E2E testing."""
    mock = MagicMock = __import__("unittest.mock").mock.MagicMock()
    mock.health_info.return_value = {
        "detector_loaded": True,
        "detector_configured": True,
        "detector_model_id": "buildborderless/CommunityForensics-DeepfakeDet-ViT",
        "cuda_available": False,
        "gpu_name": None,
        "load_error": None,
    }
    mock.infer.return_value = ModelOutput(
        model_id="buildborderless/CommunityForensics-DeepfakeDet-ViT",
        model_revision="test-rev",
        role="primary",
        status="ok",
        fake_probability=0.08,
        raw_logit=-2.44,
        threshold_policy="0.80 likely_ai / 0.05 likely_real",
        limitations=["Test model limitation"],
        device="cpu",
        duration_seconds=0.12,
    )
    app.dependency_overrides[get_detector_dependency] = lambda: mock
    return TestClient(app)


def clean_db() -> None:
    db = sync_session_factory()
    try:
        db.execute(delete(Scan))
        db.commit()
    finally:
        db.close()


def test_complete_e2e_workflow(client: TestClient) -> None:
    """
    Test complete workflow:
    1. Upload image -> runs detector, metadata, ELA, noise, frequency analyzers.
    2. Verifies evidence aggregation and verdict (LIKELY_REAL).
    3. Verifies PostgreSQL persistence.
    4. Retrieves scan from history without rerunning inference.
    5. Downloads and validates PDF forensic report.
    """
    clean_db()
    img_bytes = create_test_image_bytes()

    # 1. Upload & Analyze
    response = client.post(
        "/api/scans",
        files={"file": ("e2e_test.jpg", img_bytes, "image/jpeg")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "complete"
    scan_id = data["scan_id"]
    result = data["result"]

    # Verify input & detector & verdict
    assert result["input"]["sha256"] is not None
    assert result["models"][0]["fake_probability"] == 0.08
    assert result["verdict"]["label"] == "LIKELY_REAL"
    assert len(result["evidence_items"]) >= 5  # model + metadata + ela + noise + frequency

    # 2. Retrieve Scan History / Individual Scan
    response_get = client.get(f"/api/scans/{scan_id}")
    assert response_get.status_code == 200
    retrieved = response_get.json()
    assert retrieved["scan_id"] == scan_id
    assert retrieved["verdict"]["label"] == "LIKELY_REAL"

    # 3. List Scans (History)
    response_list = client.get("/api/scans?limit=5")
    assert response_list.status_code == 200
    list_data = response_list.json()
    assert len(list_data["scans"]) >= 1
    assert any(s["scan_id"] == scan_id for s in list_data["scans"])

    # 4. Download PDF Report
    response_pdf = client.get(f"/api/scans/{scan_id}/report.pdf")
    assert response_pdf.status_code == 200
    assert response_pdf.headers["content-type"] == "application/pdf"
    assert response_pdf.content.startswith(b"%PDF-")
    assert len(response_pdf.content) > 1000
