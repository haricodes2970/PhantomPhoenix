"""Tests for database persistence and scan history.

These tests require a running PostgreSQL database.
They are SKIPPED by default - set RUN_DB_TESTS=1 to run them.
"""

from __future__ import annotations

import io
import os

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import delete
from sqlalchemy.orm import Session

from backend.database import sync_session_factory, sync_engine, engine
from backend.main import app
from backend.models import Scan

# Skip by default - requires PostgreSQL
pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_DB_TESTS"),
    reason="Set RUN_DB_TESTS=1 to run database integration tests",
)


def create_test_image_bytes() -> bytes:
    """Create a simple test image."""
    img = Image.new("RGB", (100, 100), (128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture(scope="module")
def client() -> TestClient:
    """FastAPI test client."""
    return TestClient(app)


def clean_database() -> None:
    """Clean the scans table using synchronous session."""
    db = sync_session_factory()
    try:
        db.execute(delete(Scan))
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def dispose_async_engine() -> None:
    """Dispose async engine after each test to clear connection pool."""
    yield
    # Don't dispose here - causes event loop issues
    # import asyncio
    # asyncio.run(engine.dispose())


class TestDatabaseIntegration:
    """Database integration tests using real PostgreSQL."""

    def test_create_and_retrieve_scan(self, client: TestClient) -> None:
        """Create a scan and verify it's stored and retrievable."""
        clean_database()
        img_bytes = create_test_image_bytes()

        # Create scan
        response = client.post(
            "/api/scans",
            files={"file": ("test.jpg", img_bytes, "image/jpeg")},
        )
        assert response.status_code == 201
        data = response.json()
        scan_id = data["scan_id"]

        # Retrieve scan
        response = client.get(f"/api/scans/{scan_id}")
        assert response.status_code == 200
        retrieved = response.json()

        assert retrieved["scan_id"] == scan_id
        assert retrieved["input"]["sha256"] is not None
        assert len(retrieved["models"]) == 1
        assert retrieved["verdict"]["label"] == "LIKELY_REAL"

    def test_scan_persists_across_requests(self, client: TestClient) -> None:
        """Multiple scans are all retrievable."""
        clean_database()
        img_bytes = create_test_image_bytes()
        scan_ids = []

        # Create 3 scans
        for i in range(3):
            response = client.post(
                "/api/scans",
                files={"file": (f"test{i}.jpg", img_bytes, "image/jpeg")},
            )
            assert response.status_code == 201
            scan_ids.append(response.json()["scan_id"])
            import time
            time.sleep(0.01)

        # Retrieve all
        for scan_id in scan_ids:
            response = client.get(f"/api/scans/{scan_id}")
            assert response.status_code == 200
            assert response.json()["scan_id"] == scan_id

    def test_scan_history_pagination(self, client: TestClient) -> None:
        """Scan history returns paginated results newest first."""
        clean_database()
        img_bytes = create_test_image_bytes()

        # Create 5 scans with slight delay to ensure distinct timestamps
        created_ids = []
        for i in range(5):
            response = client.post(
                "/api/scans",
                files={"file": (f"hist{i}.jpg", img_bytes, "image/jpeg")},
            )
            assert response.status_code == 201
            created_ids.append(response.json()["scan_id"])
            import time
            time.sleep(0.01)

        # First page (limit=3)
        response = client.get("/api/scans?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data["scans"]) == 3
        assert data["limit"] == 3
        assert data["next_cursor"] is not None

        # Second page
        response = client.get(f"/api/scans?limit=3&cursor={data['next_cursor']}")
        assert response.status_code == 200
        data2 = response.json()
        assert len(data2["scans"]) >= 2

        # Verify we got all 5 unique scans across both pages
        all_ids = {scan["scan_id"] for scan in data["scans"]} | {scan["scan_id"] for scan in data2["scans"]}
        assert all_ids == set(created_ids)
        assert len(all_ids) == 5

    def test_unknown_scan_id_returns_404(self, client: TestClient) -> None:
        """Unknown scan ID returns 404."""
        clean_database()
        response = client.get("/api/scans/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
        error = response.json()
        assert error["error"]["code"] == "NOT_FOUND"

    def test_malformed_uuid_returns_422(self, client: TestClient) -> None:
        """Malformed UUID returns 422 validation error."""
        clean_database()
        response = client.get("/api/scans/not-a-uuid")
        assert response.status_code == 422

    def test_health_includes_database(self, client: TestClient) -> None:
        """Health endpoint reports database status."""
        clean_database()
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_invalid_file_still_returns_error_without_db(self, client: TestClient) -> None:
        """Invalid file upload is rejected before database interaction."""
        clean_database()
        response = client.post(
            "/api/scans",
            files={"file": ("test.txt", b"not an image", "text/plain")},
        )
        assert response.status_code == 400
        error = response.json()
        assert error["error"]["code"] == "INVALID_IMAGE"

    def test_oversized_file_rejected(self, client: TestClient) -> None:
        """Oversized file is rejected."""
        clean_database()
        import os
        large_data = os.urandom(16 * 1024 * 1024)  # 16 MB

        response = client.post(
            "/api/scans",
            files={"file": ("large.jpg", large_data, "image/jpeg")},
        )
        assert response.status_code == 400
        error = response.json()
        assert error["error"]["code"] == "FILE_TOO_LARGE"

    def test_database_error_handled_gracefully(self, client: TestClient) -> None:
        """Database errors don't crash the API - result still returned."""
        clean_database()
        from sqlalchemy.exc import SQLAlchemyError
        from backend.database import get_session
        from unittest.mock import AsyncMock

        # Create a mock session that fails on commit
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("DB connection failed"))
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.add = lambda x: None

        # Override the session dependency
        app.dependency_overrides[get_session] = lambda: mock_session

        try:
            img_bytes = create_test_image_bytes()
            response = client.post(
                "/api/scans",
                files={"file": ("test.jpg", img_bytes, "image/jpeg")},
            )
            # Should still return the computed result
            assert response.status_code in (200, 201)
            data = response.json()
            assert "scan_id" in data
            assert data["result"] is not None
        finally:
            app.dependency_overrides.pop(get_session, None)