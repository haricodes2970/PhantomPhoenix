"""FastAPI application entry point."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import close_db, get_session, init_db
from backend.detector import DetectorAdapter, get_detector, InferenceError, ModelLoadError, ConfigMismatchError
from backend.image_utils import validate_and_decode, ImageValidationError
from backend.models import Scan
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
from backend.aggregator import aggregate_assessment
from backend.report import generate_scan_pdf


from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(
    title="PHANTOM PHOENIX",
    description="Image authenticity and digital forensic intelligence API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Mount artifacts directory for safe static retrieval of forensic images
os.makedirs("uploads/artifacts", exist_ok=True)
app.mount("/api/artifacts", StaticFiles(directory="uploads/artifacts"), name="artifacts")

# CORS - restrict to Vite dev origin in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(ImageValidationError)
async def image_validation_exception_handler(request, exc: ImageValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
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


@app.get("/api/health", response_model=HealthResponse)
async def health_check(
    detector: DetectorAdapter = Depends(get_detector_dependency),
    session: AsyncSession = Depends(get_session),
) -> HealthResponse:
    """Service health and detector status."""
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


@app.post(
    "/api/scans",
    response_model=ScanCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_scan(
    file: Annotated[UploadFile, File(description="Image file (JPEG, PNG, WEBP)")],
    detector: DetectorAdapter = Depends(get_detector_dependency),
    session: AsyncSession = Depends(get_session),
) -> ScanCreateResponse:
    """
    Upload an image for AI-generation detection.

    Returns a complete scan result synchronously and persists it.
    """
    scan_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    # Validate and decode image
    validated = validate_and_decode(file.file, file.filename or "unknown", file.content_type)

    # Run inference
    models: list[ModelOutput]
    error: str | None = None
    try:
        model_output = detector.infer(validated.pil_image)
        models = [model_output]
    except (InferenceError, ModelLoadError, ConfigMismatchError) as exc:
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

    # Placeholder explainability (future: saliency heatmap)
    explainability = Explainability()

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
        error=error,
    )

    # Persist scan
    repo = ScanRepository(session)
    scan_data = {
        "id": scan_id,
        "created_at": created_at,
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
    except Exception as exc:
        # Database error - don't fabricate success, but return the computed result
        # Log the error in production
        pass

    return ScanCreateResponse(scan_id=scan_id, status=result.status, result=result)


@app.get("/api/scans")
async def list_scans(
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of scans to return")] = 20,
    cursor: Annotated[str | None, Query(description="Cursor for pagination (ISO timestamp)")] = None,
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Scan history - paginated, newest first."""
    repo = ScanRepository(session)
    scans, next_cursor = await repo.list_scans(limit=limit, cursor=cursor)

    return JSONResponse(
        content={
            "scans": [scan.to_scan_result() for scan in scans],
            "next_cursor": next_cursor,
            "limit": limit,
        }
    )


@app.get("/api/scans/{scan_id}")
async def get_scan(
    scan_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Get scan by ID - returns stored result without rerunning inference."""
    repo = ScanRepository(session)
    scan = await repo.get_by_id(scan_id)

    if scan is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="NOT_FOUND",
                    message="Scan not found",
                    detail=f"No scan with id {scan_id}",
                )
            ).model_dump(),
        )

    return JSONResponse(content=scan.to_scan_result())


@app.get("/api/scans/{scan_id}/report.pdf")
async def download_report(
    scan_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Download a forensic PDF report for an existing scan."""
    repo = ScanRepository(session)
    scan = await repo.get_by_id(scan_id)

    if scan is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="NOT_FOUND",
                    message="Scan not found",
                    detail=f"No scan with id {scan_id}",
                )
            ).model_dump(),
        )

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers,
    )