"""Tests for observability features (logging, metrics, liveness, readiness)."""

from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

from backend.logging_middleware import _safe_request_id
from backend.metrics import MetricsRegistry, normalize_route


def _override_admin() -> None:
    """Point get_current_user override at an admin identity for this test."""
    from backend.auth import RequestIdentity, get_current_user
    from backend.main import app

    admin = RequestIdentity(
        user_id="aaaaaaaa-1111-2222-3333-444444444445",
        username="test-admin",
        role="admin",
    )
    app.dependency_overrides[get_current_user] = lambda: admin


def test_liveness_endpoint(client: TestClient) -> None:
    """Liveness probe returns alive status."""
    response = client.get("/api/liveness")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_endpoint(client: TestClient, mock_detector) -> None:
    """Readiness probe returns ready status when database and detector are OK."""
    response = client.get("/api/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database_connected"] is True
    assert data["detector_configured"] is True


def test_readiness_fails_with_503_when_db_unreachable(client: TestClient, mock_detector) -> None:
    """Readiness returns 503 (probe failure) when the database is unreachable."""
    from unittest.mock import AsyncMock
    from sqlalchemy.ext.asyncio import AsyncSession
    from backend.database import get_session
    from backend.main import app

    bad_session = AsyncMock(spec=AsyncSession)
    bad_session.execute = AsyncMock(side_effect=RuntimeError("db down"))

    # Plain client (no `with`): skips startup lifespan so no real DB connect
    # is attempted — this test exercises the readiness endpoint only.
    app.dependency_overrides[get_session] = lambda: bad_session
    c = client
    response = c.get("/api/readiness")
    app.dependency_overrides.pop(get_session, None)
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["database_connected"] is False


def test_metrics_endpoint(client: TestClient) -> None:
    """Metrics endpoint exposes Prometheus exposition format (admin-only route)."""
    _override_admin()
    response = client.get("/api/metrics")
    assert response.status_code == 200
    text = response.text
    assert "# TYPE http_requests_total counter" in text
    assert "# TYPE http_request_duration_seconds histogram" in text


def test_request_id_propagation(client: TestClient) -> None:
    """Well-formed client request ID is propagated in response."""
    response = client.get("/api/liveness", headers={"X-Request-ID": "test-req-123"})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "test-req-123"


def test_invalid_request_id_is_replaced(client: TestClient) -> None:
    """Attacker-controlled request IDs (control chars / oversized) are rejected
    and replaced with a server-generated UUID, never echoed back."""
    malicious = "bad-id-with\ninjection\r-header"
    response = client.get("/api/liveness", headers={"X-Request-ID": malicious})
    assert response.status_code == 200
    returned = response.headers.get("X-Request-ID", "")
    assert returned != malicious
    assert re.match(r"^[0-9a-f-]{36}$", returned)


def test_oversized_request_id_is_replaced(client: TestClient) -> None:
    """Overlong request IDs are replaced."""
    oversized = "x" * 500
    response = client.get("/api/liveness", headers={"X-Request-ID": oversized})
    returned = response.headers.get("X-Request-ID", "")
    assert returned != oversized
    assert len(returned) <= 64


def test_safe_request_id_validation() -> None:
    """_safe_request_id accepts only safe character set and length."""
    from fastapi import Request

    class EmptyRequest:
        headers: dict[str, str] = {}

    assert re.match(r"^[0-9a-f-]{36}$", _safe_request_id(EmptyRequest()))  # type: ignore[arg-type]

    class FakeRequest:
        headers = {"X-Request-ID": "abc-123_DEF"}

    assert _safe_request_id(FakeRequest()) == "abc-123_DEF"  # type: ignore[arg-type]

    class BadRequest:
        headers = {"X-Request-ID": "spaces not allowed"}

    assert _safe_request_id(BadRequest()) != "spaces not allowed"  # type: ignore[arg-type]


def test_route_normalization_collapses_ids() -> None:
    """Scan detail UUIDs collapse to 'id' segment for bounded log/metric labels."""
    path = f"/api/scans/9b2f1e3a-1234-5678-90ab-cdef12345678/report.pdf"
    assert normalize_route(path, None) == "/api/scans/id/report.pdf"
    assert normalize_route("/api/scans/12345", None) == "/api/scans/id"
    assert normalize_route("/api/health", None) == "/api/health"
    assert normalize_route("/whatever", "/api/fixed/{scan_id}") == "/api/fixed/{scan_id}"


def test_histogram_has_buckets(client: TestClient) -> None:
    """Histogram exposition is standards-compliant (cumulative buckets, +Inf)."""
    _override_admin()
    client.get("/api/liveness")
    text = client.get("/api/metrics").text
    assert 'le="0.5"' in text
    assert 'le="+Inf"' in text
    assert "http_request_duration_seconds_bucket" in text
    assert "http_request_duration_seconds_count" in text
    assert "http_request_duration_seconds_sum" in text


def test_no_unbounded_label_values(client: TestClient) -> None:
    """Metrics never contain raw scan IDs, filenames, or hashes as labels."""
    _override_admin()
    client.get("/api/liveness")
    text = client.get("/api/metrics").text
    uuid_pattern = re.compile(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
    )
    for line in text.splitlines():
        assert not uuid_pattern.search(line), f"UUID leaked into metric line: {line}"


def test_database_connectivity_is_gauge(client: TestClient) -> None:
    """DB connectivity is exported as a gauge, refreshed per readiness check."""
    _override_admin()
    client.get("/api/readiness")
    text = client.get("/api/metrics").text
    assert "# TYPE database_connectivity_up gauge" in text
    assert re.search(r"database_connectivity_up 1", text)


def test_registry_rejects_unbounded_labels() -> None:
    """Registry refuses unbounded/unsafe label values defensively."""
    registry = MetricsRegistry()
    with pytest.raises(ValueError):
        registry.inc_counter("test_total", {"unsafe": "value with spaces"})
    with pytest.raises(ValueError):
        registry.inc_counter("test_total", {"bad name": "x"})
    # Bounded value is accepted
    registry.inc_counter("test_total", {"safe": "ok-1"})


def test_histogram_double_count_prevented() -> None:
    """One observation increments count by exactly one."""
    registry = MetricsRegistry()
    registry.observe_histogram("t_seconds", 0.2)
    registry.observe_histogram("t_seconds", 0.3)
    rendered = registry.render()
    count_line = next(l for l in rendered.splitlines() if l.startswith("t_seconds_count"))
    assert count_line.endswith(" 2")
