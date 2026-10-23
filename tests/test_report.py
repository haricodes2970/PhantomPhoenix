"""Tests for PDF report generation."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.report import generate_scan_pdf
from backend.models import Scan
from backend.main import app


def create_mock_scan() -> Scan:
    """Create a mock Scan object with realistic data."""
    scan = MagicMock(spec=Scan)
    scan.id = uuid4()
    scan.created_at = datetime.now(timezone.utc)
    scan.sha256 = "a" * 64
    scan.filename = "test_image.jpg"
    scan.media_type = "image/jpeg"
    scan.byte_size = 102400
    scan.width = 512
    scan.height = 512
    scan.status = "complete"
    scan.model_id = "buildborderless/CommunityForensics-DeepfakeDet-ViT"
    scan.model_revision = "test-revision"
    scan.model_status = "ok"
    scan.fake_probability = 0.05
    scan.raw_logit = -2.94
    scan.model_device = "cuda"
    scan.model_duration_seconds = 0.15
    scan.model_limitations = ["Test limitation"]
    scan.threshold_policy = "0.80 likely_ai / 0.05 likely_real"
    scan.verdict_label = "LIKELY_REAL"
    scan.verdict_risk = "low"
    scan.verdict_rationale = ["Primary fake probability 0.05 <= 0.2"]
    scan.verdict_not_claimed = ["generator identity", "legal authenticity", "localized forgery"]
    scan.error = None
    scan.owner_user_id = (
        "aaaaaaaa-1111-2222-3333-444444444444"  # matches conftest TEST_USER_ID
    )

    scan.to_scan_result.return_value = {
        "scan_id": str(scan.id),
        "created_at": scan.created_at.isoformat(),
        "status": "complete",
        "input": {
            "sha256": scan.sha256,
            "filename": scan.filename,
            "media_type": scan.media_type,
            "byte_size": scan.byte_size,
            "width": scan.width,
            "height": scan.height,
        },
        "models": [
            {
                "model_id": scan.model_id,
                "model_revision": scan.model_revision,
                "role": "primary",
                "status": "ok",
                "fake_probability": 0.05,
                "raw_logit": -2.94,
                "threshold_policy": "0.80 likely_ai / 0.05 likely_real",
                "limitations": ["Test limitation"],
                "device": "cuda",
                "duration_seconds": 0.15,
            }
        ],
        "indicators": [
            {
                "id": "metadata",
                "method": "computed",
                "status": "ok",
                "value": {
                    "result": {"format": "JPEG", "width": 512, "height": 512, "has_exif": False},
                    "evidence_category": "computed_observation",
                    "limitations": ["Metadata can be stripped"],
                    "error": None
                },
                "note": "Image format is JPEG (512x512, mode RGB). EXIF metadata is absent.",
                "artifact": None,
            },
        ],
        "evidence_items": [
            {"id": "test-model", "source": "ai_detector", "method": "model_inference", "evidence_category": "model_inference", "result": {}, "interpretation": "", "limitations": [], "artifact": None},
        ],
        "verdict": {
            "label": "LIKELY_REAL",
            "risk": "low",
            "rationale": ["Primary fake probability 0.05 <= 0.2"],
            "not_claimed": ["generator identity", "legal authenticity", "localized forgery", "calibrated real-world criminal fraud probability"],
        },
        "error": None,
    }

    return scan


class TestReportGeneration:
    """Tests for PDF report generation."""

    def test_generate_pdf_returns_bytes(self):
        """generate_scan_pdf returns valid PDF bytes."""
        scan = create_mock_scan()
        pdf_bytes = generate_scan_pdf(scan)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b"%PDF-")

    def test_pdf_handles_missing_artifacts(self):
        """PDF generation succeeds even when artifact files are missing."""
        scan = create_mock_scan()
        pdf_bytes = generate_scan_pdf(scan)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_pdf_handles_detector_error(self):
        """PDF generation works when detector failed."""
        scan = MagicMock()
        scan.id = uuid4()
        scan.created_at = datetime.now(timezone.utc)
        scan.sha256 = "a" * 64
        scan.filename = "test.jpg"
        scan.media_type = "image/jpeg"
        scan.byte_size = 100
        scan.width = 100
        scan.height = 100
        scan.to_scan_result.return_value = {
            "scan_id": str(scan.id),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "failed",
            "input": {"sha256": "a" * 64, "filename": "test.jpg", "media_type": "image/jpeg", "byte_size": 100, "width": 100, "height": 100},
            "models": [{"model_id": "test", "status": "error", "fake_probability": None}],
            "indicators": [],
            "evidence_items": [],
            "explainability": {"status": "unavailable", "kind": None, "artifact": None},
            "verdict": {"label": "ANALYSIS_FAILED", "risk": "unknown", "rationale": ["Detector failed"], "not_claimed": []},
            "error": "Detector unavailable",
        }
        pdf_bytes = generate_scan_pdf(scan)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0


class TestReportEndpoint:
    """Integration tests for the report endpoint."""

    def test_download_report_unknown_scan(self):
        """Unknown scan ID returns 404."""
        client = TestClient(app)
        
        # Mock repo to return None for get_by_id
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)
        
        with patch("backend.main.ScanRepository", lambda s: mock_repo):
            response = client.get(f"/api/scans/{uuid4()}/report.pdf")
            assert response.status_code == 404

    def test_download_report_success(self):
        """Successful report download for existing scan."""
        client = TestClient(app)
        mock_scan = create_mock_scan()
        
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_scan)

        with patch("backend.main.ScanRepository", lambda s: mock_repo):
            response = client.get(f"/api/scans/{mock_scan.id}/report.pdf")
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/pdf"
            assert "attachment" in response.headers.get("content-disposition", "")