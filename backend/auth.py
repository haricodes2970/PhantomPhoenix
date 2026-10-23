"""Authentication, authorization, and access policy (Milestone 12).

Security properties:
- Passwords hashed with Argon2id (argon2-cffi). No reversible representations.
- Access tokens are signed HS256 JWTs with exp/iat/iss/sub/role claims.
  Decoding uses an explicit algorithm allowlist and requires all claims.
- Tokens are delivered as an HttpOnly, SameSite=Lax cookie. The Authorization
  Bearer header is also accepted for machine clients.
- Secrets load from environment configuration; auth fails closed (503) when
  the signing secret is absent or insecurely short.
- No passwords, tokens, or authorization headers are ever logged.

Known limitations (documented, deliberate MVP tradeoffs):
- Role/enabled state is a snapshot from token issuance: disabling an account
  or revoking a role takes effect when the token expires (<= 30 min). There is
  no server-side session store or token denylist.
- Token is trusted for identity without a per-request DB lookup, keeping
  auth dependency DB-free (fast probes; enables route-level tests without
  duplicating DB machinery). Login and scan authorization DO hit the DB.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from fastapi import Depends, HTTPException, Request, status

from backend.audit import record_audit_event
from backend.config import settings
_ph = PasswordHasher()  # argon2id, sensible defaults (64MB, 3 iters, 4 lanes)

TOKEN_ALGORITHM = "HS256"          # strict allowlist; any other alg is rejected
TOKEN_ISSUER = "phantom-phoenix"
COOKIE_NAME = "phx_session"

Role = Literal["admin", "user"]


# --------------------------------------------------------------------------
# Password hashing
# --------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Hash a password with Argon2id. May raise WeakPasswordError."""
    if len(plain) < 4:
        raise WeakPasswordError("Password too short.")
    return _ph.hash(plain)


def verify_password(plain: str, password_hash: str) -> bool:
    """Constant-time Argon2id verification. Returns False on any failure."""
    try:
        return _ph.verify(password_hash, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError, ValueError):
        return False


class WeakPasswordError(ValueError):
    """Password rejected by policy."""


# --------------------------------------------------------------------------
# Token issuance / verification
# --------------------------------------------------------------------------

def get_auth_secret() -> str | None:
    """Return the signing secret, or None when absent/insecure (fail closed)."""
    secret = settings.auth_secret
    if not secret or len(secret) < 32:
        return None
    return secret


class AuthUnavailableError(HTTPException):
    """Auth configuration missing/insecure -> fail closed, generic message."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not available.",
        )


class TokenSuccess:
    __slots__ = ("token", "expires_at", "role", "user_id", "username")

    def __init__(self, token: str, expires_at: datetime, role: Role, user_id: str, username: str) -> None:
        self.token = token
        self.expires_at = expires_at
        self.role = role
        self.user_id = user_id
        self.username = username


def create_access_token(
    user_id: str, username: str, role: Role, enabled: bool = True
) -> TokenSuccess:
    """Sign a time-limited access token. Raises AuthUnavailableError fail-closed."""
    secret = get_auth_secret()
    if secret is None:
        raise AuthUnavailableError()

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "enabled": enabled,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": TOKEN_ISSUER,
    }
    token = jwt.encode(payload, secret, algorithm=TOKEN_ALGORITHM)
    return TokenSuccess(token, expires_at, role, user_id, username)


class TokenInvalidError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )


def verify_access_token(token: str) -> TokenSuccess:
    """Validate signature, algorithm, expiry, issuer and required claims.

    Raises TokenInvalidError on any malformed / expired / wrongly signed input.
    """
    secret = get_auth_secret()
    if secret is None:
        raise AuthUnavailableError()
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[TOKEN_ALGORITHM],   # strict: other algs => InvalidAlgorithmError
            options={"require": ["exp", "iat", "sub", "role", "iss", "enabled"]},
            issuer=TOKEN_ISSUER,
        )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, jwt.PyJWTError, KeyError):
        raise TokenInvalidError()

    if payload.get("enabled") is not True:
        raise TokenInvalidError()
    role = payload.get("role")
    if role not in ("admin", "user"):
        raise TokenInvalidError()
    username = str(payload.get("username") or "")
    return TokenSuccess(
        token,
        datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        role,     # type: ignore[arg-type]
        payload["sub"],
        username,
    )


# --------------------------------------------------------------------------
# Request identity
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class RequestIdentity:
    user_id: str
    username: str
    role: Role


def _extract_token(request: Request) -> str | None:
    # 1) Session cookie (browser flows: <img>, <a href>, SPA fetch)
    cookie = request.cookies.get(COOKIE_NAME)
    if cookie:
        return cookie
    # 2) Bearer header (machine clients / tests)
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        candidate = header[len("Bearer "):].strip()
        # bounded-size tokens only; avulsed tokens are simply rejected
        if 0 < len(candidate) <= 2048:
            return candidate
    return None


async def get_current_user(request: Request) -> RequestIdentity:
    """FastAPI dependency: resolve the request identity or reject.

    Raises 401 for missing/invalid tokens, 503 when auth is not configured.
    """
    raw = _extract_token(request)
    if raw is None:
        raise TokenInvalidError()
    token = verify_access_token(raw)
    return RequestIdentity(
        user_id=token.user_id,
        username=token.username,
        role=token.role,
    )


def require_role(*roles: Role):
    """Dependency factory enforcing role membership (403 otherwise)."""

    async def _guard(request: Request, user: RequestIdentity = Depends(get_current_user)) -> RequestIdentity:
        if user.role not in roles:
            await record_audit_event(
                "role_access_denied",
                outcome="denied",
                actor_user_id=user.user_id,
                actor_role=user.role,
                resource_type="route",
                request_id=getattr(request.state, "request_id", None),
                detail=str(request.scope.get("route").path) if request.scope.get("route") else None,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )
        return user

    return _guard


# --------------------------------------------------------------------------
# Scan access policy (route-level authorization over DB objects)
# --------------------------------------------------------------------------

def _normalize_uuid(value) -> str | None:
    """Normalize UUID|str|repr-ish values to canonical string; None if invalid."""
    if value is None:
        return None
    s = str(value).strip()
    if s.startswith("UUID("):
        s = s[5:-1].strip("'\"")
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1]
    try:
        return str(uuid.UUID(s))
    except (ValueError, AttributeError, TypeError):
        return None


def authorize_scan_access(user: RequestIdentity, scan) -> bool:
    """Documented access policy for scan detail/report/artifact resources.

    - Owner of the scan                        -> allowed
    - Administrator                            -> allowed (any scan, incl. legacy)
    - Ordinary user + legacy (NULL-owner) scan -> denied
    - Ordinary user + someone else's scan      -> denied

    Callers must respond to denial with HTTP 404 to avoid disclosing
    existence of other users' scans.
    """
    if user.role == "admin":
        return True
    owner = _normalize_uuid(getattr(scan, "owner_user_id", None))
    user_id = _normalize_uuid(user.user_id)
    return owner is not None and user_id is not None and owner == user_id
