"""Tests for the health endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoint_returns_ok(client: TestClient, mock_detector) -> None:
    """Health endpoint returns detector status."""
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["detector_loaded"] is True
    assert data["detector_model_id"] == "buildborderless/CommunityForensics-DeepfakeDet-ViT"
    assert data["cuda_available"] is True
    assert data["gpu_name"] == "NVIDIA RTX 3050"
    assert data["api_version"] == "0.1.0"


def test_health_endpoint_degraded_when_detector_failed(client: TestClient, mock_detector_error) -> None:
    """Health endpoint shows degraded when detector failed to load."""
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "degraded"
    assert data["detector_loaded"] is False
    assert data["detector_model_id"] is None


def test_health_alias_matches_versioned_endpoint(client: TestClient, mock_detector) -> None:
    """Unversioned /health alias returns the same payload as /api/health."""
    alias = client.get("/health")
    versioned = client.get("/api/health")

    assert alias.status_code == 200
    assert alias.json() == versioned.json()
    assert alias.json()["status"] == "ok"
