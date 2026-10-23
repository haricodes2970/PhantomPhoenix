"""FastAPI application entry point."""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import (
    COOKIE_NAME,
    RequestIdentity,
    authorize_scan_access,
    create_access_token,
    get_auth_secret,
    get_current_user,
    hash_password,
    require_role,
    verify_password,
)
from backend.logging_middleware import datetime_utc_iso, normalize_route
from backend.audit import record_audit_event
from backend.database import async_session_factory
from backend.models import AuditEvent
from backend.rate_limit import enforce_login_rate_limit, enforce_scans_rate

from backend.config import settings
from backend.database import close_db, get_session, init_db
from backend.detector import DetectorAdapter, get_detector, InferenceError, ModelLoadError, ConfigMismatchError
from backend.image_utils import validate_and_decode, ImageValidationError
from backend.models import Scan, User
from backend.repository import ScanRepository
from backend.schemas import (
    ScanResult,
    ScanCreateResponse,
    HealthResponse,
    ScanStatus,
    VerdictLabel,
    RiskLevel,
    InputDetails,
    ModelOutput,
    Indicator,
    Explainability,
    Verdict,
    ErrorResponse,
    ErrorDetail,
)
from backend.verdict import determine_verdict
from backend.forensics.runner import run_all_analyzers
from backend.aggregator import aggregate_assessment, build_investigator_report
from backend.report import generate_scan_pdf
from backend.logging_middleware import StructuredLoggingMiddleware
from backend.metrics import registry


import os
from pathlib import Path

app = FastAPI(
    title="PHANTOM PHOENIX",
    description="Image authenticity and digital forensic intelligence API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(StructuredLoggingMiddleware)

# Artifacts directory: served ONLY through the authenticated route below
# (the previous unauthenticated StaticFiles mount was removed in Milestone 12).
ARTIFACTS_BASE_DIR = Path("uploads/artifacts").resolve()
os.makedirs(ARTIFACTS_BASE_DIR, exist_ok=True)

# CORS - explicitly allowlisted origins only (configured via CORS_ORIGINS_CSV)
ALLOWED_ORIGINS = [o.strip() for o in settings.cors_origins_csv.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Authentication endpoints (Milestone 12)
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str
    password: str


async def enforce_cookie_csrf(request: Request) -> None:
    """CSRF policy for COOKIE-authenticated state-changing routes (M14).

    Policy (documented): when a request authenticates with the session
    COOKIE (no Bearer header), POST requests MUST carry an Origin header
    exactly matching the configured allowlist — browsers always send it.
    Missing or disallowed Origin -> 403. Bearer-token clients bypass this
    guard because compromised pages cannot set custom Authorization headers
    cross-site without a CORS grant.

    This is independent of SameSite=Lax (defense in depth), which already
    blocks cookies on cross-site POSTs in modern browsers.
    """
    if COOKIE_NAME not in request.cookies:
        return  # not cookie-authenticated
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return  # bearer client, not a cross-site browser submission
    origin = request.headers.get("origin")
    if not origin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing request origin.",
        )
    norm_origin = origin.replace("127.0.0.1", "localhost")
    norm_allowed = [o.replace("127.0.0.1", "localhost") for o in ALLOWED_ORIGINS]
    if norm_origin not in norm_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Request origin not allowed.",
        )


async def _optional_identity(request: Request) -> RequestIdentity | None:
    """Best-effort identity for audit attribution on public routes."""
    try:
        return await get_current_user(request)
    except Exception:
        return None


def _auth_not_ready_response() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": {
                "code": "AUTH_NOT_CONFIGURED",
                "message": "Authentication service is not available.",
            }
        },
    )


@app.post("/api/auth/login")
async def login(
    request: Request,
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(enforce_login_rate_limit),
) -> Response:
    """Authenticate and set the HttpOnly session cookie.

    Failure messages are generic and never disclose whether the username exists.
    Passwords and tokens are never logged (access middleware logs no bodies).
    """
    if get_auth_secret() is None:
        return _auth_not_ready_response()

    # CSRF layer: reject state-changing cross-origin requests by Origin
    origin = request.headers.get("origin")
    if origin and origin not in ALLOWED_ORIGINS:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": {"code": "FORBIDDEN_ORIGIN", "message": "Invalid request origin."}},
        )

    username = body.username.strip().lower()
    stmt = select(User).where(User.username == username)
    try:
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
    except Exception:
        # connectivity/unavailability handled globally (503); anything else re-raised
        raise

    request_id = getattr(request.state, "request_id", None)

    if (
        user is None
        or not user.is_enabled
        or not verify_password(body.password, user.password_hash)
    ):
        registry.inc_counter("auth_login_total", {"result": "failure"})
        # pay the Argon2 cost even for unknown users (timing-oracle mitigation)
        if user is None:
            hash_password("decoy-value-for-timing-xyz")
        await record_audit_event(
            "login_failure",
            outcome="failure",
            actor_user_id=str(user.id) if user is not None else None,
            actor_role=user.role if user is not None else None,
            resource_type="login",
            request_id=request_id,
            detail=f"user={username}",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    issued = create_access_token(str(user.id), user.username, user.role, user.is_enabled)
    registry.inc_counter("auth_login_total", {"result": "success"})
    await record_audit_event(
        "login_success",
        outcome="success",
        actor_user_id=str(user.id),
        actor_role=user.role,
        resource_type="login",
        request_id=request_id,
    )

    response = JSONResponse(
        content={
            "status": "ok",
            "role": user.role,
            "expires_at": issued.expires_at.isoformat(),
        }
    )
    response.set_cookie(
        key=COOKIE_NAME,
        value=issued.token,
        max_age=int((issued.expires_at - datetime.now(timezone.utc)).total_seconds()),
        httponly=True,
        samesite="lax",          # CSRF: blocks cross-site state-changing requests
        secure=settings.cookie_secure,  # must be True behind HTTPS in production
        path="/",
    )
    return response


@app.post("/api/auth/logout", dependencies=[Depends(enforce_cookie_csrf)])
async def logout(request: Request, response: Response) -> dict[str, str]:
    """Clear the session cookie. With stateless JWTs there is no server-side
    session store; a compromised token remains valid until expiry (documented)."""
    identity = await _optional_identity(request)
    await record_audit_event(
        "logout",
        outcome="success",
        actor_user_id=identity.user_id if identity else None,
        actor_role=identity.role if identity else None,
        resource_type="session",
        request_id=getattr(request.state, "request_id", None),
    )
    response.set_cookie(key=COOKIE_NAME, value="", max_age=0, path="/")
    return {"status": "ok"}


@app.get("/api/auth/me")
async def whoami(user: RequestIdentity = Depends(get_current_user)) -> dict[str, str]:
    """Return the authenticated identity from the validated token."""
    return {"user_id": user.user_id, "username": user.username, "role": user.role}


@app.exception_handler(ImageValidationError)
async def image_validation_exception_handler(request, exc: ImageValidationError):
    status_code = (
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        if exc.code == "FILE_TOO_LARGE"
        else status.HTTP_400_BAD_REQUEST
    )
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=ErrorDetail(code=exc.code, message=exc.message, detail=exc.detail)
        ).model_dump(),
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc: ValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                detail=str(exc),
            )
        ).model_dump(),
    )


def get_detector_dependency() -> DetectorAdapter:
    """Dependency injection for detector - returns the singleton."""
    return get_detector()


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize database on startup."""
    await init_db()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Close database connections on shutdown."""
    await close_db()


_db_failure_logger = logging.getLogger("phantom_phoenix.db")

# Connectivity-class failures treated as "service unavailable" (NOT generic
# programming errors). asyncpg connect-phase failures can surface RAW
# (e.g. socket.gaierror when DNS/service is down) without SQLAlchemy wrapping,
# so explicit classes are required. Live-verified M14.
import socket as _socket

try:  # driver-specific connection errors (asyncpg), optional at import time
    import asyncpg.exceptions as _ap_exceptions

    _DRIVER_CONNECTIVITY = tuple(
        getattr(_ap_exceptions, name)
        for name in (
            "ConnectionDoesNotExistError",
            "ConnectionFailureError",
            "ConnectionNotFoundError",
            "InterfaceError",
            "PostgresConnectionError",
            "ServerNotReadyError",
        )
        if hasattr(_ap_exceptions, name)
    )
except Exception:  # pragma: no cover - driver always present in deployment
    _DRIVER_CONNECTIVITY = ()

# builtins.ConnectionError covers ConnectionRefusedError/ConnectionResetError
_DB_CONNECTIVITY_EXC = (OperationalError, InterfaceError, _socket.gaierror, ConnectionError, TimeoutError) + _DRIVER_CONNECTIVITY


# Connectivity-class failures treated as "service unavailable" (NOT generic
# programming errors). asyncpg connect-phase failures can surface RAW
# (e.g. socket.gaierror when DNS/service is down) without SQLAlchemy wrapping,
# so explicit classes are required. Live-verified M14.
import socket as _socket

try:  # driver-specific connection errors (asyncpg), optional at import time
    import asyncpg.exceptions as _ap_exceptions

    _DRIVER_CONNECTIVITY = tuple(
        getattr(_ap_exceptions, name)
        for name in (
            "ConnectionDoesNotExistError",
            "ConnectionFailureError",
            "ConnectionNotFoundError",
            "InterfaceError",
            "PostgresConnectionError",
            "ServerNotReadyError",
        )
        if hasattr(_ap_exceptions, name)
    )
except Exception:  # pragma: no cover - driver always present in deployment
    _DRIVER_CONNECTIVITY = ()

# builtins.ConnectionError covers ConnectionRefusedError/ConnectionResetError
_DB_CONNECTIVITY_EXC = (
    OperationalError,
    InterfaceError,
    _socket.gaierror,
    ConnectionError,
    TimeoutError,
) + _DRIVER_CONNECTIVITY


async def database_unavailable_handler(request: Request, exc: Exception):
    """Connectivity-level DB failures -> generic 503 (not 500).

    Distinguishes availability failures from programming errors:
    - Connectivity-class failures -> 503, sanitized log once (category +
      correlation ID only; never SQL, DSN, or stack details).
    - Everything else propagates to Starlette's generic 500 handler.
    """
    request_id = getattr(request.state, "request_id", None)
    _db_failure_logger.error(
        json.dumps({
            "timestamp": datetime_utc_iso(),
            "severity": "ERROR",
            "request_id": request_id,
            "method": request.method,
            "route": request.url.path,
            "exception_category": "database_unavailable",
            "message": "Database temporarily unavailable.",
        })
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"error": {"code": "SERVICE_UNAVAILABLE", "message": "Service temporarily unavailable. Please try again later."}},
    )


# Registered one class at a time (this Starlette version rejects tuples).
for _exc_cls in _DB_CONNECTIVITY_EXC:
    app.add_exception_handler(_exc_cls, database_unavailable_handler)  # type: ignore[arg-type]


@app.get("/health", response_model=HealthResponse, include_in_schema=False)
@app.get("/api/health", response_model=HealthResponse)
async def health_check(
    detector: DetectorAdapter = Depends(get_detector_dependency),
    session: AsyncSession = Depends(get_session),
) -> HealthResponse:
    """Service health and detector status.

    Exposed at both /api/health (documented, used by the frontend/tooling) and
    /health (unversioned alias for external/local health probes).
    """
    info = detector.health_info()
    cuda_available = info["cuda_available"]

    # Check database connectivity
    db_ok = False
    try:
        await session.execute(select(1))
        db_ok = True
    except Exception:
        db_ok = False

    # OK if detector is configured (no load error) and DB is reachable
    status_value = "ok" if info["detector_configured"] and db_ok else "degraded"

    return HealthResponse(
        status=status_value,
        detector_loaded=info["detector_loaded"],
        detector_model_id=info["detector_model_id"],
        cuda_available=cuda_available,
        gpu_name=info["gpu_name"],
    )


@app.get("/api/liveness")
async def liveness_check() -> dict[str, str]:
    """Liveness probe - confirms API process is running."""
    return {"status": "alive"}


@app.get("/api/readiness")
async def readiness_check(
    detector: DetectorAdapter = Depends(get_detector_dependency),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Readiness probe - confirms database connectivity and detector configuration.

    Returns 200 when the service can safely accept scan workloads, 503 otherwise.
    Detector readiness here means "configured and able to accept a scan request";
    model weights load lazily on first inference and are NOT forced by this probe.
    """
    db_ok = False
    try:
        await session.execute(select(1))
        db_ok = True
    except Exception:
        db_ok = False
    registry.set_gauge("database_connectivity_up", 1.0 if db_ok else 0.0)

    info = detector.health_info()
    ready = info["detector_configured"] and db_ok

    payload = {
        "status": "ready" if ready else "not_ready",
        "database_connected": db_ok,
        "detector_configured": info["detector_configured"],
        "detector_loaded": info["detector_loaded"],
    }
    return JSONResponse(status_code=200 if ready else 503, content=payload)


@app.get("/api/metrics", include_in_schema=False)
async def metrics_endpoint(
    user: RequestIdentity = Depends(require_role("admin")),
) -> PlainTextResponse:
    """Prometheus metrics endpoint (administrator / authorized operators only).

    Deployment note: consolidate scraping behind a trusted internal monitoring
    boundary (e.g. an authenticated reverse proxy in front of this endpoint).
    Machine clients may authenticate with an admin bearer token.
    """
    return PlainTextResponse(registry.render(), media_type="text/plain; version=0.0.4")


@app.post(
    "/api/scans",
    response_model=ScanCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_scans_rate), Depends(enforce_cookie_csrf)],
)
async def create_scan(
    file: Annotated[UploadFile, File(description="Image file (JPEG, PNG, WEBP)")],
    request: Request,
    user: RequestIdentity = Depends(get_current_user),
    detector: DetectorAdapter = Depends(get_detector_dependency),
    session: AsyncSession = Depends(get_session),
) -> ScanCreateResponse:
    """
    Upload an image for AI-generation detection (authenticated users only).

    Returns a complete scan result synchronously and persists it.
    """
    scan_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)
    try:
        owner_id = uuid.UUID(user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.") from exc

    # Validate and decode image
    validated = validate_and_decode(file.file, file.filename or "unknown", file.content_type)

    # Run inference
    models: list[ModelOutput]
    error: str | None = None
    try:
        model_output = detector.infer(validated.pil_image, str(scan_id))
        models = [model_output]
        registry.inc_counter("detector_inference_total", {"status": "success"})
        if model_output.duration_seconds is not None:
            registry.observe_histogram("detector_inference_duration_seconds", model_output.duration_seconds)
    except (InferenceError, ModelLoadError, ConfigMismatchError) as exc:
        registry.inc_counter("detector_inference_total", {"status": "failure"})
        models = [
            ModelOutput(
                model_id=settings.model_id,
                model_revision="",
                role="primary",
                status="error",
                fake_probability=None,
                raw_logit=None,
                limitations=[],
            )
        ]
        error = str(exc)

    # Build input details
    input_details = InputDetails(
        sha256=validated.sha256,
        filename=validated.original_filename,
        media_type=validated.media_type,
        byte_size=validated.byte_size,
        width=validated.width,
        height=validated.height,
    )

    # Run forensic analyzers (metadata, ELA, noise, frequency)
    indicators = run_all_analyzers(validated, scan_id)

    # Aggregate evidence and determine verdict
    assessment = aggregate_assessment(
        models=models,
        indicators=indicators,
        likely_ai_threshold=settings.likely_ai_threshold,
        likely_real_threshold=settings.likely_real_threshold,
    )
    verdict = assessment.verdict
    registry.inc_counter("scan_outcomes_total", {"outcome": verdict.label})

    # Populate explainability from model output if available
    primary_model = next((m for m in models if m.role == "primary"), None)
    exp_data = primary_model.explainability if primary_model and primary_model.explainability else {}
    explainability = Explainability(
        status=exp_data.get("status", "unavailable"),
        kind=exp_data.get("kind", "attention_rollout"),
        artifact=exp_data.get("artifact"),
        metrics=exp_data.get("metrics", {}),
    )

    # Build six-part investigator evidence report
    investigator_report = build_investigator_report(
        scan_id=str(scan_id),
        created_at=created_at.isoformat(),
        input_details=input_details,
        models=models,
        indicators=indicators,
        verdict=verdict,
        assessment=assessment,
    )

    result = ScanResult(
        scan_id=scan_id,
        created_at=created_at.isoformat(),
        status=ScanStatus.COMPLETE if error is None else ScanStatus.FAILED,
        input=input_details,
        models=models,
        indicators=indicators,
        evidence_items=assessment.evidence_items,
        explainability=explainability,
        verdict=verdict,
        investigator_report=investigator_report,
        error=error,
    )

    # Persist scan
    repo = ScanRepository(session)
    scan_data = {
        "id": scan_id,
        "created_at": created_at,
        "owner_user_id": owner_id,
        "status": result.status,
        "sha256": validated.sha256,
        "filename": validated.original_filename,
        "media_type": validated.media_type,
        "byte_size": validated.byte_size,
        "width": validated.width,
        "height": validated.height,
        "model_id": models[0].model_id if models else None,
        "model_revision": models[0].model_revision if models else None,
        "model_status": models[0].status if models else None,
        "fake_probability": models[0].fake_probability if models else None,
        "raw_logit": models[0].raw_logit if models else None,
        "model_device": models[0].device if models else None,
        "model_duration_seconds": models[0].duration_seconds if models else None,
        "model_limitations": models[0].limitations if models else None,
        "threshold_policy": models[0].threshold_policy if models else None,
        "verdict_label": verdict.label,
        "verdict_risk": verdict.risk,
        "verdict_rationale": verdict.rationale,
        "verdict_not_claimed": verdict.not_claimed,
        "error": error,
        "full_result": result.model_dump(mode="json"),
    }

    try:
        await repo.create(scan_data)
    except Exception:
        # Persistence failure must never be reported as a successful scan.
        # Roll back explicitly because the session dependency commits after the
        # endpoint returns normally. Log only a sanitized category/request ID;
        # exception text may contain credentials or SQL details.
        await session.rollback()
        _db_failure_logger.error(
            json.dumps({
                "timestamp": datetime_utc_iso(),
                "severity": "ERROR",
                "request_id": getattr(request.state, "request_id", None),
                "method": request.method,
                "route": "/api/scans",
                "exception_category": "scan_persistence_failed",
                "message": "Scan result could not be persisted.",
            })
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "code": "SCAN_PERSISTENCE_UNAVAILABLE",
                    "message": "Scan could not be saved. Please try again later.",
                }
            },
        )

    return ScanCreateResponse(scan_id=scan_id, status=result.status, result=result)


@app.get("/api/scans")
async def list_scans(
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of scans to return")] = 20,
    cursor: Annotated[str | None, Query(description="Cursor for pagination (ISO timestamp)")] = None,
    user: RequestIdentity = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Scan history - paginated, newest first.

    Ordinary users see only their own scans. Administrators see all scans
    (including legacy NULL-owner records, per the documented access policy).
    """
    repo = ScanRepository(session)
    if user.role == "admin":
        scans, next_cursor = await repo.list_scans(limit=limit, cursor=cursor, include_unowned=True)
    else:
        scans, next_cursor = await repo.list_scans(limit=limit, cursor=cursor, owner_user_id=uuid.UUID(user.user_id))

    return JSONResponse(
        content={
            "scans": [scan.to_scan_result() for scan in scans],
            "next_cursor": next_cursor,
            "limit": limit,
        }
    )


def _not_found_response() -> JSONResponse:
    """Uniform 404 used for missing AND forbidden resources (no existence disclosure)."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ErrorResponse(
            error=ErrorDetail(
                code="NOT_FOUND",
                message="Scan not found",
            )
        ).model_dump(),
    )


async def _get_authorized_scan(
    scan_id: uuid.UUID,
    user: RequestIdentity,
    session: AsyncSession,
    request_id: str | None = None,
):
    """Shared route-level authorization for detail/report/artifact access."""
    scan = await ScanRepository(session).get_by_id(scan_id)
    if scan is None or not authorize_scan_access(user, scan):
        return None

    # Administrative access to OTHER users' scans / legacy NULL-owner records
    # (M14 audit). Own scans deliberately not audited (noise reduction).
    owner = getattr(scan, "owner_user_id", None)
    if user.role == "admin" and (owner is None or str(owner) != str(user.user_id)):
        await record_audit_event(
            "admin_legacy_scan_access" if owner is None else "admin_cross_user_access",
            outcome="success",
            actor_user_id=user.user_id,
            actor_role=user.role,
            resource_type="scan",
            resource_id=str(scan_id),
            request_id=request_id,
        )
    return scan


@app.get("/api/scans/{scan_id}")
async def get_scan(
    scan_id: uuid.UUID,
    request: Request,
    user: RequestIdentity = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Get scan by ID - returns stored result without rerunning inference."""
    scan = await _get_authorized_scan(scan_id, user, session, getattr(request.state, "request_id", None))
    if scan is None:
        return _not_found_response()

    return JSONResponse(content=scan.to_scan_result())


@app.get("/api/scans/{scan_id}/report.pdf")
async def download_report(
    scan_id: uuid.UUID,
    request: Request,
    user: RequestIdentity = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Download a forensic PDF report for an existing scan."""
    scan = await _get_authorized_scan(scan_id, user, session, getattr(request.state, "request_id", None))
    if scan is None:
        return _not_found_response()

    try:
        pdf_bytes = generate_scan_pdf(scan)
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="REPORT_GENERATION_FAILED",
                    message="Failed to generate PDF report",
                    detail=str(exc),
                )
            ).model_dump(),
        )

    from fastapi.responses import Response

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="phantom_phoenix_report_{scan_id}.pdf"'
        },
    )


@app.get("/api/artifacts/{artifact_path:path}", include_in_schema=False)
async def serve_artifact(
    artifact_path: str,
    request: Request,
    user: RequestIdentity = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Authenticated, traversal-safe access to forensic artifact images.

    Replaces the previous unauthenticated StaticFiles mount (Milestone 12).
    Path structure is {scan_uuid}/{filename}; the scan UUID segment is used
    for the documented ownership policy. Any path-escape attempt returns 404.
    """
    rel = Path(artifact_path)
    if not artifact_path or rel.is_absolute() or ".." in rel.parts:
        return _not_found_response()

    scan_uuid = None
    if len(rel.parts) >= 1:
        try:
            scan_uuid = uuid.UUID(rel.parts[0])
        except ValueError:
            scan_uuid = None
    if scan_uuid is None:
        return _not_found_response()

    scan = await _get_authorized_scan(scan_uuid, user, session, getattr(request.state, "request_id", None))
    if scan is None:
        return _not_found_response()

    target = (ARTIFACTS_BASE_DIR / rel).resolve()
    # resolve() collapses ../ and symlinks; enforce containment
    if target != ARTIFACTS_BASE_DIR and ARTIFACTS_BASE_DIR not in target.parents:
        return _not_found_response()
    if not target.is_file():
        return _not_found_response()

    return FileResponse(target, filename=target.name)


@app.get("/api/admin/audit")
async def read_audit_events(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    event_type: Annotated[str | None, Query(max_length=64)] = None,
    user: RequestIdentity = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Admin-only inspection of the security audit trail. Ordinary users
    receive 403; there are deliberately NO update/delete routes. Bounded
    values only (event_type charset enforced below)."""
    if event_type is not None and not re.fullmatch(r"[a-z_]{1,64}", event_type or ""):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid event_type filter.")
    stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset)
    if event_type:
        stmt = stmt.where(AuditEvent.event_type == event_type)
    result = await session.execute(stmt)
    events = list(result.scalars().all())
    total_stmt = select(func.count()).select_from(AuditEvent)
    if event_type:
        total_stmt = total_stmt.where(AuditEvent.event_type == event_type)
    total = (await session.execute(total_stmt)).scalar_one()
    return JSONResponse(content={
        "total": int(total),
        "events": [
            {
                "id": str(e.id),
                "created_at": e.created_at.isoformat(),
                "actor_user_id": str(e.actor_user_id) if e.actor_user_id else None,
                "actor_role": e.actor_role,
                "event_type": e.event_type,
                "outcome": e.outcome,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "request_id": e.request_id,
                "detail": e.detail,
            }
            for e in events
        ],
    })


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers,
    )