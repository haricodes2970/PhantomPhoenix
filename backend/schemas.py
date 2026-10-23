"""Pydantic schemas for API requests and responses."""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict
from typing import Literal


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
    threshold_policy: str = "0.80 likely_ai / 0.05 likely_real"
    limitations: list[str] = Field(default_factory=list)
    device: str | None = None
    duration_seconds: float | None = None
    explainability: dict[str, Any] | None = None


class Indicator(BaseModel):
    """Forensic indicator (placeholder for future expansion)."""

    id: str
    method: str  # computed, heuristic, verified, unknown
    status: str  # present, absent, stripped, unverified, not_checked, error
    value: dict[str, Any] = Field(default_factory=dict)
    note: str = ""
    artifact: str | None = None


class Explainability(BaseModel):
    """Explainability artifact / attention analysis."""

    status: str = "unavailable"
    kind: str | None = None
    artifact: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


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
    investigator_report: InvestigatorEvidenceReport | None = None
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


# =============================================================================
# Six-Part Investigator Evidence Report Schemas (Milestone 2)
# =============================================================================

class FileIntegrityProvenance(BaseModel):
    """Section 1: File Integrity and Provenance."""

    model_config = ConfigDict(use_enum_values=True)

    sha256: str
    original_filename: str
    internal_identifier: str
    file_format: str
    dimensions: str  # "WIDTH x HEIGHT px"
    file_size_bytes: int
    exif_fields: dict[str, str] = Field(default_factory=dict)
    xmp_present: bool = False
    missing_metadata_observations: list[str] = Field(default_factory=list)
    integrity_status: Literal["verified", "unverified", "corrupted"] = "verified"
    provenance_status: Literal["established", "partial", "unknown"] = "unknown"
    scan_id: str
    analysis_timestamp_utc: str


class SourceDiscovery(BaseModel):
    """Section 2: Source Discovery."""

    model_config = ConfigDict(use_enum_values=True)

    status: Literal["searched", "not_searched", "error"] = "not_searched"
    candidate_urls: list[str] = Field(default_factory=list)
    match_method: str | None = None
    match_strength: Literal["exact", "near", "none", "unknown"] = "unknown"
    supporting_evidence: list[str] = Field(default_factory=list)
    publication_timestamps: list[str] = Field(default_factory=list)
    earliest_known_source: bool = False
    limitations: list[str] = Field(default_factory=list)


class PublisherIntelligence(BaseModel):
    """Section 3: Publisher and Account Intelligence."""

    model_config = ConfigDict(use_enum_values=True)

    status: Literal["identified", "unknown", "not_searched", "error"] = "unknown"
    account_name: str | None = None
    source_url: str | None = None
    relationship: str | None = None  # uploader, creator, distributor, unknown
    verification_status: Literal["verified", "unverified", "disputed", "unknown"] = "unknown"
    limitations: list[str] = Field(default_factory=list)


class GeneratorAttribution(BaseModel):
    """Section 4: Generator and Editing Attribution."""

    model_config = ConfigDict(use_enum_values=True)

    status: Literal["ok", "unsupported", "error"] = "unsupported"
    method: Literal["model_inference", "provenance", "unknown"] = "unknown"
    candidates: list[dict[str, Any]] = Field(default_factory=list)  # family, confidence, evidence_type
    limitations: list[str] = Field(default_factory=list)
    error: str | None = None


class ExternalInvestigationEvidence(BaseModel):
    """Section 5: External Investigation Evidence."""

    model_config = ConfigDict(use_enum_values=True)

    status: Literal["available", "not_available", "not_authorized", "error"] = "not_available"
    platform_records: list[dict[str, Any]] = Field(default_factory=list)
    publication_timestamps: list[str] = Field(default_factory=list)
    public_urls: list[str] = Field(default_factory=list)
    account_records: list[dict[str, Any]] = Field(default_factory=list)
    network_audit_evidence: list[dict[str, Any]] = Field(default_factory=list)
    source: str | None = None
    retrieval_time_utc: str | None = None
    access_limitations: list[str] = Field(default_factory=list)
    verification_status: Literal["verified", "unverified", "unknown"] = "unknown"


class EvidencePreservation(BaseModel):
    """Section 6: Evidence Preservation and Corroboration."""

    model_config = ConfigDict(use_enum_values=True)

    original_file_hash: str
    scan_identifier: str
    analysis_timestamp_utc: str
    detector_version: str
    forensic_versions: dict[str, str] = Field(default_factory=dict)
    supporting_observations: list[str] = Field(default_factory=list)
    artifact_references: list[str] = Field(default_factory=list)
    evidence_relationships: list[str] = Field(default_factory=list)
    audit_events: list[dict[str, Any]] = Field(default_factory=list)
    integrity_checks: list[str] = Field(default_factory=list)
    corroboration_status: Literal["corroborated", "partial", "unverified", "contradicted"] = "unverified"
    outstanding_questions: list[str] = Field(default_factory=list)


class InvestigatorEvidenceReport(BaseModel):
    """Complete six-part investigator evidence report."""

    model_config = ConfigDict(use_enum_values=True)

    section_1_file_integrity: FileIntegrityProvenance
    section_2_source_discovery: SourceDiscovery
    section_3_publisher_intelligence: PublisherIntelligence
    section_4_generator_attribution: GeneratorAttribution
    section_5_external_evidence: ExternalInvestigationEvidence
    section_6_evidence_preservation: EvidencePreservation