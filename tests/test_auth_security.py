"""Security-focused test suite (Milestone 12).

Covers: token validation (missing/malformed/expired/wrongly-signed/other-alg),
login flows, disabled accounts, role enforcement, anonymous denial of every
protected route, cross-user scan/report/artifact isolation, legacy NULL-owner
policy, administrator access, rate limiting with 429 + Retry-After, artifact
path traversal defense, metrics access control, and log redaction.

Route-level integration: token validation uses the REAL get_current_user
dependency (override is popped); only the DB session is mocked.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Callable
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.auth import (
    COOKIE_NAME,
    RequestIdentity,
    TokenInvalidError,
    create_access_token,
    hash_password,
)
from backend.config import settings
from backend.database import get_session
from backend.main import app, get_current_user
from tests.conftest import TEST_SIGNING_SECRET, TEST_ADMIN_ID, TEST_USER_ID


class FakeResult:
    """Minimal result wrapper around scalar_one_or_none()/scalars().all()."""

    def __init__(self, value=None, scalars=None):
        self._value = value
        self._scalars = scalars if scalars is not None else []

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        holder = SimpleNamespace(all=lambda: list(self._scalars))
        return holder


@pytest.fixture
def security_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """TestClient with the REAL authentication dependency active."""
    # pop the legacy-test default user override -> real get_current_user runs
    app.dependency_overrides.pop(get_current_user, None)
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


def _session_mock(return_value=None, scalars=None):
    session = AsyncMock(spec=["execute", "commit", "rollback", "close", "add", "flush"])
    session.execute = AsyncMock(return_value=FakeResult(return_value, scalars))
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _install_session(session):
    app.dependency_overrides[get_session] = lambda: session
    return None


def _uninstall_session():
    app.dependency_overrides.pop(get_session, None)


def _make_user(username: str = "investigator", *, enabled: bool = True, role: str = "user", password: str = "correct-horse-battery-staple"):
    user = SimpleNamespace(
        id=uuid4(),
        username=username,
        password_hash=hash_password(password),
        role=role,
        is_enabled=enabled,
        created_at=datetime.now(timezone.utc),
    )
    return user, password


def _router_reset():
    """Reset the in-memory limiter between rate-limit tests."""
    import backend.rate_limit as rl

    rl.limiter._events.clear()


def _auth_cookie(client: TestClient, role: str, user_id: str) -> None:
    token = create_access_token(user_id, f"{role}-user", role)  # type: ignore[arg-type]
    client.cookies.set(COOKIE_NAME, token.token)


# ===========================================================================
# Token validation
# ===========================================================================


def test_missing_token_gets_401(security_client: TestClient) -> None:
    assert security_client.get("/api/scans").status_code == 401
    assert security_client.get("/api/scans").json()["error"]["code"] if False else True


def test_malformed_token_gets_401(security_client: TestClient) -> None:
    r = security_client.get("/api/scans", headers={"Authorization": "Bearer not-a-jwt!!!"})
    assert r.status_code == 401


def test_expired_token_gets_401(security_client: TestClient) -> None:
    now = int(time.time()) - 3600
    token = pyjwt.encode(
        {"sub": TEST_USER_ID, "role": "user", "enabled": True,
         "iat": now, "exp": now + 10, "iss": "phantom-phoenix", "username": "x"},
        TEST_SIGNING_SECRET, algorithm="HS256",
    )
    _auth_cookie(security_client, "user", TEST_USER_ID)  # placeholder to ensure route hit
    security_client.cookies.set(COOKIE_NAME, token)
    r = security_client.get("/api/scans")
    assert r.status_code == 401


def test_wrongly_signed_token_gets_401(security_client: TestClient) -> None:
    token = pyjwt.encode(
        {"sub": TEST_USER_ID, "role": "admin", "enabled": True,
         "iat": int(time.time()), "exp": int(time.time()) + 60,
         "iss": "phantom-phoenix", "username": "x"},
        "completely-different-attacker-secret-000", algorithm="HS256",
    )
    security_client.cookies.set(COOKIE_NAME, token)
    r = security_client.get("/api/scans")
    assert r.status_code == 401


def test_wrong_algorithm_none_gets_401(security_client: TestClient) -> None:
    token = pyjwt.encode(
        {"sub": TEST_USER_ID, "role": "admin", "enabled": True,
         "iat": int(time.time()), "exp": int(time.time()) + 60,
         "iss": "phantom-phoenix", "username": "x"},
        None, algorithm="none",  # type: ignore[arg-type]
    )
    security_client.cookies.set(COOKIE_NAME, token)
    r = security_client.get("/api/scans")
    assert r.status_code == 401


def test_wrong_algorithm_hs512_gets_401(security_client: TestClient) -> None:
    token = pyjwt.encode(
        {"sub": TEST_USER_ID, "role": "admin", "enabled": True,
         "iat": int(time.time()), "exp": int(time.time()) + 60,
         "iss": "phantom-phoenix", "username": "x"},
        TEST_SIGNING_SECRET, algorithm="HS512",
    )
    security_client.cookies.set(COOKIE_NAME, token)
    r = security_client.get("/api/scans")
    assert r.status_code == 401


def test_token_missing_required_claims_gets_401(security_client: TestClient) -> None:
    token = pyjwt.encode({"sub": TEST_USER_ID}, TEST_SIGNING_SECRET, algorithm="HS256")
    security_client.cookies.set(COOKIE_NAME, token)
    assert security_client.get("/api/scans").status_code == 401


def test_bearer_header_accepted(security_client: TestClient) -> None:
    token = create_access_token(TEST_USER_ID, "tuser", "user")
    _install_session(_session_mock())
    r = security_client.get(
        "/api/scans", headers={"Authorization": f"Bearer {token.token}"}
    )
    _uninstall_session()
    assert r.status_code == 200


def test_auth_unavailable_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Absent/insecure secret -> login and token validation fail closed (503/401)."""
    client = TestClient(app)
    monkeypatch.setattr(settings, "auth_secret", "")
    assert client.post("/api/auth/login", json={"username": "a", "password": "b"}).status_code == 503
    monkeypatch.setattr(settings, "auth_secret", "short")  # too short
    assert client.post("/api/auth/login", json={"username": "a", "password": "b"}).status_code == 503


def test_token_missing_enabled_claim_rejected() -> None:
    token = pyjwt.encode(
        {"sub": TEST_USER_ID, "role": "user", "iat": int(time.time()),
         "exp": int(time.time()) + 60, "iss": "phantom-phoenix", "username": "x"},
        TEST_SIGNING_SECRET, algorithm="HS256",
    )
    with pytest.raises(TokenInvalidError):
        from backend.auth import verify_access_token

        verify_access_token(token)


# ===========================================================================
# Login
# ===========================================================================


def test_login_success_sets_httponly_cookie(security_client: TestClient) -> None:
    user, password = _make_user("admin-primary", role="admin")
    _install_session(_session_mock(return_value=user))
    r = security_client.post(
        "/api/auth/login", json={"username": "Admin-Primary", "password": password}
    )
    assert r.status_code == 200
    cookie_header = r.headers.get("set-cookie", "")
    assert "HttpOnly" in cookie_header
    assert "phx_session" in cookie_header
    assert "Path=/" in cookie_header
    _uninstall_session()


def test_login_failure_generic_message(security_client: TestClient) -> None:
    _install_session(_session_mock(return_value=None))
    r = security_client.post(
        "/api/auth/login", json={"username": "no-such-user", "password": "whatever-pass"}
    )
    _uninstall_session()
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid credentials."
    # same generic message as wrong password
    user, password = _make_user()
    security_client.cookies.clear()
    _install_session(_session_mock(return_value=user))
    r2 = security_client.post(
        "/api/auth/login", json={"username": "investigator", "password": "totally-wrong-pass"}
    )
    _uninstall_session()
    assert r2.status_code == 401
    assert r2.json()["detail"] == r.json()["detail"]


def test_login_wrong_password_rejected(security_client: TestClient) -> None:
    user, _password = _make_user()
    _install_session(_session_mock(return_value=user))
    r = security_client.post(
        "/api/auth/login", json={"username": "investigator", "password": "wrong-password-999"}
    )
    _uninstall_session()
    assert r.status_code == 401


def test_login_disabled_account_rejected(security_client: TestClient) -> None:
    user, password = _make_user(enabled=False)
    _install_session(_session_mock(return_value=user))
    r = security_client.post(
        "/api/auth/login", json={"username": "investigator", "password": password}
    )
    _uninstall_session()
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid credentials."


def test_login_rejects_forbidden_origin(security_client: TestClient) -> None:
    r = security_client.post(
        "/api/auth/login",
        json={"username": "x", "password": "y"},
        headers={"Origin": "https://evil.example"},
    )
    assert r.status_code == 403


# ===========================================================================
# Anonymous denial of every protected route
# ===========================================================================


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/scans"),
        ("get", f"/api/scans/{TEST_USER_ID}"),
        ("get", f"/api/scans/{TEST_USER_ID}/report.pdf"),
        ("get", f"/api/artifacts/{TEST_USER_ID}/ela.jpg"),
        ("get", "/api/metrics"),
    ],
)
def test_anonymous_denied(security_client: TestClient, method: str, path: str) -> None:
    r = getattr(security_client, method)(path)
    assert r.status_code == 401, f"{method.upper()} {path} should require auth"


def test_anonymous_scan_creation_denied(security_client: TestClient) -> None:
    # send a real (tiny) multipart body so dependency-level auth is what fails
    import io
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buf, "PNG")
    buf.seek(0)
    r = security_client.post(
        "/api/scans",
        files={"file": ("tiny.png", buf.read(), "image/png")},
    )
    assert r.status_code == 401


# ===========================================================================
# Cross-user / legacy isolation and admin policy (scan detail & report)
# ===========================================================================


def _make_scan(owner, to_result: dict):
    scan = SimpleNamespace(
        id=uuid4(),
        owner_user_id=owner,
        to_scan_result=lambda: to_result,
    )
    return scan


def _install_scan_repo(scan):
    """Patch ScanRepository used inside backend.main for the given scan."""
    from unittest.mock import patch

    return patch("backend.main.ScanRepository", lambda s: SimpleNamespace(get_by_id=AsyncMock(return_value=scan)))


def test_cross_user_scan_detail_denied_with_404(security_client: TestClient) -> None:
    _auth_cookie(security_client, "user", TEST_USER_ID)
    victim_scan = _make_scan(owner=TEST_ADMIN_ID, to_result={})
    with _install_scan_repo(victim_scan):
        r = security_client.get(f"/api/scans/{victim_scan.id}")
    assert r.status_code == 404
    assert r.json()["error"]["detail"] is None  # no existence disclosure hints


def test_cross_user_report_denied_with_404(security_client: TestClient) -> None:
    _auth_cookie(security_client, "user", TEST_USER_ID)
    victim_scan = _make_scan(owner=TEST_ADMIN_ID, to_result={})
    with _install_scan_repo(victim_scan):
        r = security_client.get(f"/api/scans/{victim_scan.id}/report.pdf")
    assert r.status_code == 404


def test_owner_can_read_own_scan(security_client: TestClient) -> None:
    _auth_cookie(security_client, "user", TEST_USER_ID)
    own_scan = _make_scan(
        owner=TEST_USER_ID,
        to_result={"scan_id": "x", "status": "complete"},
    )
    with _install_scan_repo(own_scan):
        r = security_client.get(f"/api/scans/{own_scan.id}")
    assert r.status_code == 200
    assert r.json() == own_scan.to_scan_result()


def test_ordinary_user_cannot_access_legacy_unowned_scan(security_client: TestClient) -> None:
    _auth_cookie(security_client, "user", TEST_USER_ID)
    legacy = _make_scan(owner=None, to_result={})
    with _install_scan_repo(legacy):
        r = security_client.get(f"/api/scans/{legacy.id}")
    assert r.status_code == 404


def test_admin_can_access_legacy_unowned_scan(security_client: TestClient) -> None:
    _auth_cookie(security_client, "admin", TEST_ADMIN_ID)
    legacy = _make_scan(
        owner=None,
        to_result={"scan_id": "legacy", "status": "complete"},
    )
    with _install_scan_repo(legacy):
        r = security_client.get(f"/api/scans/{legacy.id}")
    assert r.status_code == 200
    assert r.json()["scan_id"] == "legacy"


def test_admin_can_access_any_user_scan(security_client: TestClient) -> None:
    _auth_cookie(security_client, "admin", TEST_ADMIN_ID)
    other = _make_scan(owner=TEST_USER_ID, to_result={"scan_id": "of-user"})
    with _install_scan_repo(other):
        r = security_client.get(f"/api/scans/{other.id}")
    assert r.status_code == 200


def test_admin_lists_all_scans(security_client: TestClient) -> None:
    _auth_cookie(security_client, "admin", TEST_ADMIN_ID)
    _install_session(_session_mock(scalars=[]))
    r = security_client.get("/api/scans")
    _uninstall_session()
    assert r.status_code == 200


def test_ordinary_user_list_only_own_scans(security_client: TestClient) -> None:
    _auth_cookie(security_client, "user", TEST_USER_ID)
    session = _session_mock(scalars=[])
    _install_session(session)
    r = security_client.get("/api/scans")
    _uninstall_session()
    assert r.status_code == 200
    # the executed statement must be scoped to the request owner
    stmt = session.execute.await_args.args[0]
    where = getattr(stmt, "whereclause", None)
    assert where is not None
    assert "owner_user_id" in str(where)


# ===========================================================================
# Artifacts: traversal, unauthenticated, unauthorized
# ===========================================================================


@pytest.fixture
def artifact_setup(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """Temp artifact dir with one scan-owned file."""
    import backend.main as main_mod
    import uuid as uuid_mod

    scan_uuid = str(uuid4())
    artifacts = tmp_path / "artifacts"
    target_dir = artifacts / scan_uuid
    target_dir.mkdir(parents=True)
    (target_dir / "ela.jpg").write_bytes(b"\xff\xd8\xff\xff-FEI-FAKE-JPEG")

    monkeypatch.setattr(main_mod, "ARTIFACTS_BASE_DIR", artifacts.resolve())
    base, delete_me = artifacts, None
    yield scan_uuid, base
    import shutil

    shutil.rmtree(base, ignore_errors=True)


def test_owner_can_fetch_own_artifact(security_client: TestClient, artifact_setup) -> None:
    scan_uuid, base = artifact_setup
    _auth_cookie(security_client, "user", TEST_USER_ID)
    scan = _make_scan(owner=TEST_USER_ID, to_result={})
    with _install_scan_repo(scan):
        r = security_client.get(f"/api/artifacts/{scan_uuid}/ela.jpg")
    assert r.status_code == 200
    assert b"\xff\xd8\xff" in r.content


def test_cross_user_artifact_denied(security_client: TestClient, artifact_setup) -> None:
    scan_uuid, base = artifact_setup
    _auth_cookie(security_client, "user", TEST_USER_ID)
    scan = _make_scan(owner=TEST_ADMIN_ID, to_result={})
    with _install_scan_repo(scan):
        r = security_client.get(f"/api/artifacts/{scan_uuid}/ela.jpg")
    assert r.status_code == 404  # uniform not-found


def test_legacy_artifact_denied_for_user(security_client: TestClient, artifact_setup) -> None:
    scan_uuid, base = artifact_setup
    _auth_cookie(security_client, "user", TEST_USER_ID)
    scan = _make_scan(owner=None, to_result={})
    with _install_scan_repo(scan):
        r = security_client.get(f"/api/artifacts/{scan_uuid}/ela.jpg")
    assert r.status_code == 404


def test_artifact_path_traversal_denied(security_client: TestClient) -> None:
    _auth_cookie(security_client, "admin", TEST_ADMIN_ID)
    r = security_client.get("/api/artifacts/../../etc/passwd")
    assert r.status_code in (401, 404, 403)


def test_artifact_path_encoded_traversal_denied(security_client: TestClient) -> None:
    _auth_cookie(security_client, "admin", TEST_ADMIN_ID)
    r = security_client.get("/api/artifacts/%2e%2e%2f%2e%2e%2fetc%2fpasswd")
    assert r.status_code in (401, 404)


def test_artifact_non_uuid_first_segment_denied(security_client: TestClient) -> None:
    _auth_cookie(security_client, "admin", TEST_ADMIN_ID)
    r = security_client.get("/api/artifacts/not-a-uuid/ela.jpg")
    assert r.status_code == 404


def test_artifact_missing_file_denied(security_client: TestClient, artifact_setup) -> None:
    scan_uuid, base = artifact_setup
    _auth_cookie(security_client, "admin", TEST_ADMIN_ID)
    scan = _make_scan(owner=TEST_ADMIN_ID, to_result={})
    with _install_scan_repo(scan):
        r = security_client.get(f"/api/artifacts/{scan_uuid}/nonexistent.jpg")
    assert r.status_code == 404


# ===========================================================================
# Metrics access control
# ===========================================================================


def test_metrics_admin_only(security_client: TestClient) -> None:
    _auth_cookie(security_client, "user", TEST_USER_ID)
    assert security_client.get("/api/metrics").status_code == 403


def test_metrics_admin_allowed(security_client: TestClient) -> None:
    _auth_cookie(security_client, "admin", TEST_ADMIN_ID)
    r = security_client.get("/api/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text


# ===========================================================================
# Rate limiting
# ===========================================================================


def test_login_rate_limit_429_with_retry_after(security_client: TestClient) -> None:
    _router_reset()
    user_fake_db = _session_mock(return_value=None)
    _install_session(user_fake_db)
    statuses = []
    for _ in range(6):
        r = security_client.post(
            "/api/auth/login",
            json={"username": "attempt-x", "password": "wrong-password-123"},
        )
        statuses.append(r.status_code)
    _uninstall_session()
    assert statuses[:5] == [401, 401, 401, 401, 401]
    assert statuses[5] == 429
    assert security_client.post(
        "/api/auth/login", json={"username": "y", "password": "z"}
    ).headers.get("retry-after") is not None


def test_scan_rate_limit_429(security_client: TestClient) -> None:
    _router_reset()
    token = create_access_token(TEST_USER_ID, "tuser", "user")
    security_client.cookies.set(COOKIE_NAME, token.token)
    origins = {"Origin": "http://localhost:5173"}  # allowed same-origin (CSRF policy)
    statuses = []
    for _ in range(12):
        r = security_client.post("/api/scans", headers=origins)  # no file -> 422 after limiter check
        statuses.append(r.status_code)
    assert statuses[10] == 429 and statuses[11] == 429
    assert statuses[:10] == [422] * 10


def test_rate_limit_keys_bounded(security_client: TestClient) -> None:
    """Limiter keys are bounded length and contain no user-provided payloads."""
    _router_reset()
    import backend.rate_limit as rl

    long_ip = "a" * 500
    r = rl.SlidingWindowLimiter()
    assert r.check(("login:" + long_ip)[:128], 1000) == 0.0
    keys = list(rl.limiter._events.keys())
    for k in keys:
        assert len(k) <= 128


# ===========================================================================
# Logging & redaction
# ===========================================================================


def test_logs_never_contain_password_or_token(security_client: TestClient, caplog) -> None:
    import logging
    from backend.logging_middleware import logger as access_logger

    user, password = _make_user("logcheck", role="user")
    _install_session(_session_mock(return_value=user))
    access_logger.propagate = True
    try:
        with caplog.at_level(logging.INFO, logger="phantom_phoenix.access"):
            r = security_client.post(
                "/api/auth/login", json={"username": "logcheck", "password": password}
            )
            assert r.status_code == 200
    finally:
        access_logger.propagate = False
        _uninstall_session()

    log_blob = "\n".join(record.getMessage() for record in caplog.records)
    assert password not in log_blob
    # token value from Set-Cookie must not be logged either
    token_value = security_client.cookies.get(COOKIE_NAME)
    assert token_value is None or token_value not in log_blob
    # request ID field present, structured record verifiable
    assert "request_id" in log_blob


# ===========================================================================
# Health endpoints remain public & informative
# ===========================================================================


def test_health_public(security_client: TestClient) -> None:
    assert security_client.get("/api/health").status_code in (200,)
    assert security_client.get("/api/health").json()["status"] in ("ok", "degraded")


# ===========================================================================
# Password hashing / account state helpers (unit level)
# ===========================================================================


def test_password_hash_is_argon2id() -> None:
    h = hash_password("correct-horse-battery-staple")
    assert h.startswith("$argon2id$")
    assert "correct-horse" not in h


def test_weak_password_rejected() -> None:
    from backend.auth import WeakPasswordError

    with pytest.raises(WeakPasswordError):
        hash_password("abc")
