"""Pydantic schemas for API requests and responses."""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ScanStatus(str, Enum):
    """Scan processing status."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class VerdictLabel(str, Enum):
    """Final verdict labels."""

    LIKELY_AI = "LIKELY_AI"
    LIKELY_REAL = "LIKELY_REAL"
    INCONCLUSIVE = "INCONCLUSIVE"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"


class RiskLevel(str, Enum):
    """Risk assessment levels."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    UNKNOWN = "unknown"


class ModelOutput(BaseModel):
    """Single model inference output."""

    model_id: str
    model_revision: str
    role: str = "primary"
    status: str = "ok"  # ok, unavailable, error
    fake_probability: float | None = None
    raw_logit: float | None = None
    threshold_policy: str = "0.80 likely_ai / 0.20 likely_real"
    limitations: list[str] = Field(default_factory=list)
    device: str | None = None
    duration_seconds: float | None = None


class Indicator(BaseModel):
    """Forensic indicator (placeholder for future expansion)."""

    id: str
    method: str  # computed, heuristic, verified, unknown
    status: str  # present, absent, stripped, unverified, not_checked, error
    value: dict[str, Any] = Field(default_factory=dict)
    note: str = ""
    artifact: str | None = None


class Explainability(BaseModel):
    """Explainability artifact (placeholder)."""

    status: str = "unavailable"
    kind: str | None = None
    artifact: str | None = None


class Verdict(BaseModel):
    """Final verdict with rationale."""

    label: VerdictLabel
    risk: RiskLevel
    rationale: list[str] = Field(default_factory=list)
    not_claimed: list[str] = Field(default_factory=list)


class NormalizedEvidenceItem(BaseModel):
    """Normalized evidence item with full traceability."""

    id: str
    source: str  # "ai_detector" | "forensic_metadata" | "forensic_ela" | "forensic_noise" | "forensic_frequency"
    method: str  # "computed" | "heuristic" | "verified" | "model_inference" | "unknown"
    status: str  # "ok" | "error" | "not_applicable" | "present" | "absent"
    evidence_category: str  # "model_inference" | "computed_observation" | "heuristic" | "verified_evidence" | "unknown_or_unavailable"
    result: dict[str, Any] = Field(default_factory=dict)
    interpretation: str = ""
    limitations: list[str] = Field(default_factory=list)
    artifact: str | None = None


class InputDetails(BaseModel):
    """Details about the uploaded input image."""

    sha256: str
    filename: str
    media_type: str
    byte_size: int
    width: int
    height: int


class ScanResult(BaseModel):
    """Complete scan result returned to the client."""

    scan_id: UUID
    created_at: str  # ISO 8601
    status: ScanStatus
    input: InputDetails
    models: list[ModelOutput]
    indicators: list[Indicator] = Field(default_factory=list)
    evidence_items: list[NormalizedEvidenceItem] = Field(default_factory=list)
    explainability: Explainability = Field(default_factory=Explainability)
    verdict: Verdict
    error: str | None = None

    model_config = ConfigDict(use_enum_values=True)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str  # ok, degraded
    api_version: str = "0.1.0"
    detector_loaded: bool
    detector_model_id: str | None = None
    cuda_available: bool
    gpu_name: str | None = None


class ScanCreateResponse(BaseModel):
    """Response after creating a scan (sync path returns full result)."""

    scan_id: UUID
    status: ScanStatus
    result: ScanResult | None = None


# Error responses
class ErrorDetail(BaseModel):
    """Standard error detail."""

    code: str
    message: str
    detail: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: ErrorDetail