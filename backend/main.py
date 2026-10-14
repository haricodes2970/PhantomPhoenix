"""FastAPI application entry point."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.config import settings
from backend.detector import DetectorAdapter, get_detector, InferenceError, ModelLoadError, ConfigMismatchError
from backend.image_utils import validate_and_decode, ImageValidationError
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
from backend.config import settings


app = FastAPI(
    title="PHANTOM PHOENIX",
    description="Image authenticity and digital forensic intelligence API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

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


@app.get("/api/health", response_model=HealthResponse)
async def health_check(detector: DetectorAdapter = Depends(get_detector_dependency)) -> HealthResponse:
    """Service health and detector status."""
    info = detector.health_info()
    cuda_available = info["cuda_available"]
    # OK if detector is configured (no load error) even if not yet loaded
    status_value = "ok" if info["detector_configured"] else "degraded"

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
) -> ScanCreateResponse:
    """
    Upload an image for AI-generation detection.

    Returns a complete scan result synchronously.
    For production use with larger models, this would return 202 and a scan ID for polling.
    """
    scan_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc).isoformat()

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

    # Determine verdict
    verdict = determine_verdict(models, settings.likely_ai_threshold, settings.likely_real_threshold)

    # Placeholder indicators (future: EXIF, ELA, noise, C2PA)
    indicators: list[Indicator] = []

    # Placeholder explainability (future: saliency heatmap)
    explainability = Explainability()

    result = ScanResult(
        scan_id=scan_id,
        created_at=created_at,
        status=ScanStatus.COMPLETE if error is None else ScanStatus.FAILED,
        input=input_details,
        models=models,
        indicators=indicators,
        explainability=explainability,
        verdict=verdict,
        error=error,
    )

    return ScanCreateResponse(scan_id=scan_id, status=result.status, result=result)


# Optional: scan history endpoint (stub - would need DB in future)
@app.get("/api/scans")
async def list_scans() -> JSONResponse:
    """Scan history - not implemented without database."""
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=ErrorResponse(
            error=ErrorDetail(
                code="NOT_IMPLEMENTED",
                message="Scan history requires database (not implemented in this task)",
            )
        ).model_dump(),
    )


@app.get("/api/scans/{scan_id}")
async def get_scan(scan_id: uuid.UUID) -> JSONResponse:
    """Get scan by ID - not implemented without database."""
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=ErrorResponse(
            error=ErrorDetail(
                code="NOT_IMPLEMENTED",
                message="Scan retrieval requires database (not implemented in this task)",
            )
        ).model_dump(),
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