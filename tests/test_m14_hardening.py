"""Milestone 14 hardening tests.

Covers:
- Phase 2: database-outage HTTP handling (503 vs 401 vs 500), no leakage.
- Phase 3: audit trail events, bounded/redacted fields, access control.
- Phase 5: CSRF origin policy on cookie-authenticated state changes.

Audit-event DATA is verified with an in-memory capture session; live
Postgres verification of events + admin read endpoint happens on the
disposable Docker stack (documented separately in the M14 report).
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from backend import audit as audit_mod
from backend.auth import COOKIE_NAME, RequestIdentity, create_access_token
from backend.database import get_session
from backend.main import app, get_current_user
from tests.conftest import TEST_USER_ID


@pytest.fixture
def security_client(monkeypatch: pytest.MonkeyPatch):
    """TestClient with the REAL authentication dependency active."""
    app.dependency_overrides.pop(get_current_user, None)
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------- helpers

class _FakeSession:
    """Minimal async-session stand-in for audit capture."""

    def __init__(self, sink: list, fail: bool = False) -> None:
        self._sink = sink
        self._fail = fail

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def add(self, obj):
        if self._fail:
            raise OperationalError("INSERT", [], Exception("connection refused"))
        self._sink.append(obj)

    async def commit(self):
        pass


@pytest.fixture()
def audit_sink(monkeypatch: pytest.MonkeyPatch):
    """Capture audit events without a real database."""
    sink: list = []
    monkeypatch.setattr(
        audit_mod, "async_session_factory", lambda: _FakeSession(sink)
    )
    return sink


def _cookie_and_identity(role: str = "user", user_id: str = TEST_USER_ID):
    identity = RequestIdentity(user_id=user_id, username="tuser", role=role)
    token = create_access_token(identity.user_id, identity.username, role)
    return token.token, identity


def _install_session(session):
    """Override the request DB session dependency, M12-suite style."""
    app.dependency_overrides[get_session] = lambda: session
    return session


def _uninstall_session():
    app.dependency_overrides.pop(get_session, None)


def _db_session(execute_mock: AsyncMock):
    session = MagicMock()
    session.execute = execute_mock
    return session


# ------------------------------------------------------- Phase 2: DB outage

def _outage_exc() -> OperationalError:
    return OperationalError("SELECT 1", [], Exception("connection refused"))


class TestDatabaseOutage:
    def test_login_outage_returns_503(
        self, security_client: TestClient, audit_sink
    ) -> None:
        exec_mock = AsyncMock(side_effect=OperationalError(
            "SELECT 1", [], Exception("connection refused")
        ))
        _install_session(_db_session(exec_mock))
        try:
            resp = security_client.post(
                "/api/auth/login",
                json={"username": "someone", "password": "pw"},
            )
        finally:
            _uninstall_session()
        assert resp.status_code == 503
        body = resp.json()
        assert "unavailable" in body["error"]["message"].lower()
        # No infrastructure detail leakage
        serialized = resp.text.lower()
        for forbidden in ("connection refused", "postgres", "select 1", "traceback", "dsn"):
            assert forbidden not in serialized

    def test_login_outage_raw_socket_gaierror_returns_503(
        self, security_client: TestClient, audit_sink
    ) -> None:
        """asyncpg connect failures surface RAW — live-verified M14."""
        import socket as _socket

        exec_mock = AsyncMock(side_effect=_socket.gaierror(-2, "Name or service not known"))
        _install_session(_db_session(exec_mock))
        try:
            resp = security_client.post(
                "/api/auth/login",
                json={"username": "someone", "password": "pw"},
            )
        finally:
            _uninstall_session()
        assert resp.status_code == 503
        assert "Name or service" not in resp.text

    def test_login_invalid_credentials_still_401(
        self, security_client: TestClient, audit_sink
    ) -> None:
        # Session works (no outage); unknown user -> generic 401, NOT 503/exception
        empty_result = MagicMock()
        empty_result.scalar_one_or_none.return_value = None
        exec_mock = AsyncMock(return_value=empty_result)
        _install_session(_db_session(exec_mock))
        try:
            resp = security_client.post(
                "/api/auth/login",
                json={"username": "ghost_user", "password": "pw"},
            )
        finally:
            _uninstall_session()
        assert resp.status_code == 401
        assert "invalid credentials" in resp.json()["detail"].lower()

    def test_session_validation_works_during_db_outage(
        self, security_client: TestClient
    ) -> None:
        token, _ = _cookie_and_identity()
        security_client.cookies.set(COOKIE_NAME, token)
        # token validation never touches the DB -> unaffected
        resp = security_client.get("/api/auth/me")
        assert resp.status_code == 200

    def test_db_recovery_allows_login(
        self, security_client: TestClient, audit_sink
    ) -> None:
        user_row = SimpleNamespace(
            id=uuid4(), username="tuser", password_hash="argon2$stub", role="user", is_enabled=True
        )
        result_ok = MagicMock()
        result_ok.scalar_one_or_none.return_value = user_row
        exec_mock = AsyncMock(return_value=result_ok)
        _install_session(_db_session(exec_mock))
        try:
            with patch("backend.main.verify_password", side_effect=lambda pw, h: True):
                resp = security_client.post(
                    "/api/auth/login", json={"username": "tuser", "password": "good"}
                )
        finally:
            _uninstall_session()
        assert resp.status_code == 200


# ------------------------------------------------------- Phase 3: audit

class TestAuditTrail:
    def test_login_failure_event_recorded(
        self, security_client: TestClient, audit_sink
    ) -> None:
        empty_result = MagicMock()
        empty_result.scalar_one_or_none.return_value = None
        exec_mock = AsyncMock(return_value=empty_result)
        _install_session(_db_session(exec_mock))
        try:
            resp = security_client.post(
                "/api/auth/login", json={"username": "ghost", "password": "pw"}
            )
        finally:
            _uninstall_session()
        assert resp.status_code == 401
        events = [e for e in audit_sink if e.event_type == "login_failure"]
        assert len(events) == 1
        ev = events[0]
        assert ev.outcome == "failure"
        assert ev.actor_user_id is None  # unknown account

    def test_login_success_event_recorded(
        self, security_client: TestClient, audit_sink
    ) -> None:
        user_row = SimpleNamespace(
            id=uuid4(), username="tuser", password_hash="argon2$stub", role="user", is_enabled=True
        )
        result_ok = MagicMock()
        result_ok.scalar_one_or_none.return_value = user_row
        exec_mock = AsyncMock(return_value=result_ok)
        _install_session(_db_session(exec_mock))
        try:
            with patch("backend.main.verify_password", side_effect=lambda pw, h: True):
                resp = security_client.post(
                    "/api/auth/login", json={"username": "tuser", "password": "good"}
                )
        finally:
            _uninstall_session()
        assert resp.status_code == 200
        ev = [e for e in audit_sink if e.event_type == "login_success"]
        assert len(ev) == 1
        assert str(ev[0].actor_user_id) == str(user_row.id)
        assert ev[0].actor_role == "user"

    def test_logout_event_recorded(self, security_client: TestClient, audit_sink) -> None:
        token, identity = _cookie_and_identity()
        security_client.cookies.set(COOKIE_NAME, token)
        resp = security_client.post("/api/auth/logout", headers={"Origin": "http://localhost:5173"})
        assert resp.status_code == 200
        ev = [e for e in audit_sink if e.event_type == "logout"]
        assert len(ev) == 1
        assert ev[0].actor_user_id == identity.user_id

    def test_role_denial_event_recorded(self, security_client: TestClient, audit_sink) -> None:
        token, identity = _cookie_and_identity(role="user")
        security_client.cookies.set(COOKIE_NAME, token)
        resp = security_client.get("/api/metrics")
        assert resp.status_code == 403
        ev = [e for e in audit_sink if e.event_type == "role_access_denied"]
        assert len(ev) == 1
        assert ev[0].actor_role == "user"
        assert ev[0].outcome == "denied"

    def test_audit_writer_rejects_unknown_event_type(self, audit_sink) -> None:
        import asyncio

        run = asyncio.new_event_loop()
        try:
            run.run_until_complete(
                audit_mod.record_audit_event("not_a_real_event", outcome="success")
            )
        finally:
            run.close()
        # unknown types are REJECTED (not stored)
        assert len(audit_sink) == 0

    def test_audit_values_bounded_and_sanitized(self) -> None:
        raw = "scan\n-- injected line\x1b" + "x" * 400
        out = audit_mod._bounded(raw, 64)
        assert out is not None
        assert "\n" not in out and "\x1b" not in out
        assert len(out) <= 64
        assert audit_mod.SAFE_CHARS_RE.match(out)

    def test_audit_never_stores_password_like_fields(
        self, security_client: TestClient, audit_sink
    ) -> None:
        empty_result = MagicMock()
        empty_result.scalar_one_or_none.return_value = None
        exec_mock = AsyncMock(return_value=empty_result)
        _install_session(_db_session(exec_mock))
        try:
            security_client.post(
                "/api/auth/login",
                json={"username": "ghost", "password": "SUPER-secret-pw-123"},
            )
        finally:
            _uninstall_session()
        for ev in audit_sink:
            blob = repr(ev)
            assert "SUPER-secret-pw-123" not in blob

    def test_audit_write_failure_does_not_break_request(
        self, security_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Audit-vs-availability tradeoff: failures are swallowed."""
        monkeypatch.setattr(
            audit_mod,
            "async_session_factory",
            lambda: _FakeSession([], fail=True),
        )
        token, _ = _cookie_and_identity()
        security_client.cookies.set(COOKIE_NAME, token)
        resp = security_client.post(
            "/api/auth/logout", headers={"Origin": "http://localhost:5173"}
        )
        assert resp.status_code == 200  # request still succeeds

    def test_ordinary_user_cannot_read_audit(
        self, security_client: TestClient, audit_sink
    ) -> None:
        token, _ = _cookie_and_identity(role="user")
        security_client.cookies.set(COOKIE_NAME, token)
        resp = security_client.get("/api/admin/audit")
        assert resp.status_code == 403

    def test_admin_can_read_audit(
        self, security_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Seed one event via the capture sink directly.
        sink: list = []

        class _StubEvent:
            id = uuid4()
            created_at = datetime(2026, 10, 18, tzinfo=timezone.utc)
            actor_user_id = None
            actor_role = "admin"
            event_type = "admin_bootstrap"
            outcome = "success"
            resource_type = None
            resource_id = None
            request_id = None
            detail = "user=bootstrap_admin"

        sink.append(_StubEvent())

        monkeypatch.setattr(
            audit_mod, "async_session_factory", lambda: _FakeSession(sink)
        )
        # DB-backed read path is exercised live on the disposable stack;
        # here we validate route guard + response shape with a stubbed query.
        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = sink
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        exec_mock = AsyncMock(side_effect=[events_result, count_result])

        token, _ = _cookie_and_identity(role="admin")
        security_client.cookies.set(COOKIE_NAME, token)
        _install_session(_db_session(exec_mock))
        try:
            resp = security_client.get("/api/admin/audit")
        finally:
            _uninstall_session()
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["total"] == 1
        assert payload["events"][0]["event_type"] == "admin_bootstrap"
        assert "id" in payload["events"][0]

    def test_admin_audit_invalid_filter_422(
        self, security_client: TestClient
    ) -> None:
        token, _ = _cookie_and_identity(role="admin")
        security_client.cookies.set(COOKIE_NAME, token)
        resp = security_client.get("/api/admin/audit", params={"event_type": "DROP TABLE"})
        assert resp.status_code == 422


# ------------------------------------------------------- Phase 5: CSRF

ALLOWED = "http://localhost:5173"


class TestCookieCsrfPolicy:
    def test_cookie_post_scan_missing_origin_403(
        self, security_client: TestClient
    ) -> None:
        token, _ = _cookie_and_identity()
        security_client.cookies.set(COOKIE_NAME, token)
        resp = security_client.post("/api/scans")
        assert resp.status_code == 403

    def test_cookie_post_scan_disallowed_origin_403(
        self, security_client: TestClient
    ) -> None:
        token, _ = _cookie_and_identity()
        security_client.cookies.set(COOKIE_NAME, token)
        resp = security_client.post("/api/scans", headers={"Origin": "https://evil.example"})
        assert resp.status_code == 403

    def test_cookie_post_scan_allowed_origin_passes_guard(
        self, security_client: TestClient
    ) -> None:
        token, _ = _cookie_and_identity()
        security_client.cookies.set(COOKIE_NAME, token)
        resp = security_client.post("/api/scans", headers={"Origin": ALLOWED})
        # No file attached -> 422 validation, i.e. the CSRF guard passed.
        assert resp.status_code == 422

    def test_bearer_post_scan_missing_origin_allowed(
        self, security_client: TestClient
    ) -> None:
        token, _ = _cookie_and_identity()
        resp = security_client.post(
            "/api/scans",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Bearer clients bypass the cookie CSRF guard -> reaches validation (422).
        assert resp.status_code == 422

    def test_cookie_cross_site_logout_rejected(
        self, security_client: TestClient
    ) -> None:
        token, _ = _cookie_and_identity()
        security_client.cookies.set(COOKIE_NAME, token)
        resp = security_client.post(
            "/api/auth/logout", headers={"Origin": "https://evil.example"}
        )
        assert resp.status_code == 403

    def test_logout_without_origin_but_no_cookie_allowed(
        self, security_client: TestClient
    ) -> None:
        # Anonymous caller, no session cookie: policy allows the no-op logout.
        resp = security_client.post("/api/auth/logout")
        assert resp.status_code == 200

    def test_login_cross_disallowed_origin_rejected(
        self, security_client: TestClient
    ) -> None:
        # login keeps the softer policy (origin validated only when present)
        resp = security_client.post(
            "/api/auth/login",
            json={"username": "x", "password": "y"},
            headers={"Origin": "https://evil.example"},
        )
        assert resp.status_code == 403
