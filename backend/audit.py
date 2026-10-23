"""Security audit trail writer (Milestone 14).

Design decisions (documented):
- Events are written through a DEDICATED short-lived session that commits
  immediately, independent of the request transaction. This avoids losing
  denial events on request rollback and keeps audit failures from corrupting
  the request path.
- Audit failures NEVER break unrelated successful operations (including
  reads); they are logged once, sanitized, and swallowed. Explicit tradeoff:
  availability over forced audit atomicity. (A database administrator can
  still modify the underlying table — this is NOT a tamper-proof ledger.)
- Bounded values only: event types from a fixed set; dynamic strings are
  clamped and charset-normalized (no newlines, bounded length) so no forged
  log entries or unbounded values can be stored.
- No recursive logging: audit writes emit no new audit events.
- Never stored: passwords, tokens, cookies, image bytes, raw request bodies,
  EXIF metadata.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import uuid
from datetime import datetime, timezone

from backend.database import async_session_factory
from backend.models import AuditEvent

_audit_logger = logging.getLogger("phantom_phoenix.audit")
_audit_logger.setLevel(logging.INFO)
if not _audit_logger.handlers:
    _audit_logger.addHandler(logging.StreamHandler(sys.stderr))
    _audit_logger.propagate = False

KNOWN_EVENT_TYPES = frozenset({
    "login_success",
    "login_failure",
    "logout",
    "admin_bootstrap",
    "admin_legacy_scan_access",
    "admin_cross_user_access",
    "role_access_denied",
})

SAFE_CHARS_RE = re.compile(r"^[A-Za-z0-9_\-\.:/]{1,255}$")


def _bounded(value: str | None, max_len: int = 255) -> str | None:
    """Return a bounded, forge-proof string (charset-normalized)."""
    if value is None:
        return None
    candidate = str(value).strip()
    if not candidate:
        return None
    if not SAFE_CHARS_RE.match(candidate):
        candidate = re.sub(r"[^A-Za-z0-9_\-\.:/]", "_", candidate)
    return candidate[:max_len] or None


def _as_uuid(actor_user_id: str | uuid.UUID | None) -> str | None:
    """Accept UUID/string; normalize to canonical UUID string or None."""
    if actor_user_id is None:
        return None
    try:
        return str(uuid.UUID(str(actor_user_id)))
    except (ValueError, AttributeError, TypeError):
        return None


async def record_audit_event(
    event_type: str,
    *,
    outcome: str,
    actor_user_id: str | uuid.UUID | None = None,
    actor_role: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    request_id: str | None = None,
    detail: str | None = None,
) -> None:
    """Write one audit event. Never raises; never logs sensitive payloads."""
    if event_type not in KNOWN_EVENT_TYPES:
        _audit_logger.warning(json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": "WARNING",
            "message": "audit_rejected_unknown_event_type",
            "event_type": _bounded(event_type, 64),
        }))
        return
    if outcome not in ("success", "failure", "denied"):
        outcome = "failure"

    event = AuditEvent(
        actor_user_id=_as_uuid(actor_user_id),
        actor_role=_bounded(actor_role, 32),
        event_type=_bounded(event_type, 64),
        outcome=outcome,  # type: ignore[arg-type]
        resource_type=_bounded(resource_type, 32),
        resource_id=_bounded(resource_id, 64),
        request_id=_bounded(request_id, 64),
        detail=_bounded(detail, 255),
    )

    try:
        async with async_session_factory() as session:
            session.add(event)
            await session.commit()
    except Exception as exc:
        # never break the request path; log once, sanitized (class name only)
        _audit_logger.error(json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": "ERROR",
            "exception_category": "audit_write_failed",
            "event_type": _bounded(event_type, 64),
        }))
        _audit_logger.debug("audit write failure class: %s", type(exc).__name__)
