"""Attribution service schemas."""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, ConfigDict


class AttributionStatus(str, Enum):
    """Attribution service status."""

    OK = "ok"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


class AttributionMethod(str, Enum):
    """How the attribution was derived."""

    MODEL_INFERENCE = "model_inference"
    VERIFIED_PROVENANCE = "verified_provenance"
    UNKNOWN = "unknown"


class CandidateFamily(BaseModel):
    """A candidate generator/editing family with confidence."""

    model_config = ConfigDict(use_enum_values=True)

    family: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_type: AttributionMethod
    metadata: dict[str, Any] = Field(default_factory=dict)


class AttributionResult(BaseModel):
    """Complete generator/editing attribution result."""

    model_config = ConfigDict(use_enum_values=True)

    status: AttributionStatus
    method: AttributionMethod
    candidates: list[CandidateFamily] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    error: str | None = None


def create_unsupported_result() -> AttributionResult:
    """Create an 'unsupported' attribution result for deployments without attribution capability."""
    return AttributionResult(
        status=AttributionStatus.UNSUPPORTED,
        method=AttributionMethod.UNKNOWN,
        candidates=[],
        limitations=[
            "Generator/editing attribution is not available in this deployment.",
            "No attribution model is loaded or licensed for inference.",
            "Binary AI detection does not imply generator identification.",
        ],
    )


def create_error_result(error_msg: str) -> AttributionResult:
    """Create an error attribution result."""
    return AttributionResult(
        status=AttributionStatus.ERROR,
        method=AttributionMethod.UNKNOWN,
        candidates=[],
        limitations=["Attribution service encountered an error."],
        error=error_msg,
    )