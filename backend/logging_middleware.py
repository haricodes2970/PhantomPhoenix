"""Structured JSON request logging middleware with request ID propagation.

Security properties:
- Request IDs are validated (alphanumeric/dash/underscore, max 64 chars);
  invalid or oversized client-supplied values are replaced with a fresh UUID,
  so attacker-controlled data never lands in response headers or log lines.
- Request bodies, uploaded image content, credentials, authorization headers,
  and query strings are never logged.
- Routes are normalized to bounded templates (UUID/numeric IDs collapsed)
  before being used in log fields or metric labels.
- Exceptions are logged once as a category name; stack traces and absolute
  filesystem paths never reach clients or access logs.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.metrics import normalize_route, registry

logger = logging.getLogger("phantom_phoenix.access")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


def _safe_request_id(request: Request) -> str:
    """Accept a well-formed client request ID; otherwise generate a UUID."""
    candidate = request.headers.get("X-Request-ID", "")
    if candidate and _REQUEST_ID_RE.match(candidate):
        return candidate
    return str(uuid.uuid4())


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Emit one sanitized JSON access-log line per request and record metrics."""

    async def dispatch(self, request: Request, call: Callable) -> Response:
        request_id = _safe_request_id(request)
        request.state.request_id = request_id

        start_time = time.perf_counter()
        status_code = 500
        exception_category: str | None = None
        response: Response | None = None

        try:
            response = await call(request)
            status_code = response.status_code
        except Exception as exc:
            exception_category = type(exc).__name__
            raise
        finally:
            duration_seconds = time.perf_counter() - start_time
            route = normalize_route(
                request.url.path,
                getattr(request.scope.get("route"), "path", None),
            )
            severity = "ERROR" if status_code >= 500 else "INFO"
            log_record = {
                "timestamp": datetime_utc_iso(),
                "severity": severity,
                "request_id": request_id,
                "method": request.method,
                "route": route,
                "status_code": status_code,
                "status_class": f"{status_code // 100}xx",
                "duration_ms": round(duration_seconds * 1000.0, 2),
            }
            if exception_category:
                log_record["exception_category"] = exception_category
            logger.info(json.dumps(log_record))

            try:
                registry.observe_http_request(
                    request.method, route, status_code, duration_seconds
                )
            except Exception:
                # Instrumentation must never break the request path.
                pass

        if response is not None:
            response.headers["X-Request-ID"] = request_id
        return response


def datetime_utc_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
