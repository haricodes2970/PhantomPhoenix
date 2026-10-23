"""Forensic analysis base types and interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from PIL import Image


@dataclass(frozen=True)
class ForensicResult:
    """Standardized output from a forensic analyzer."""

    id: str
    status: str  # "ok", "error", "not_applicable"
    method: str  # "computed", "heuristic", "verified", "model_inference", "unknown"
    result: dict[str, Any] = field(default_factory=dict)
    interpretation: str = ""
    evidence_category: str = "computed"  # "computed", "heuristic", "verified", "model_inference", "unknown"
    limitations: list[str] = field(default_factory=list)
    artifact: str | None = None  # Relative path to generated artifact image
    error: str | None = None


@dataclass(frozen=True)
class ForensicContext:
    """Context passed to each analyzer containing image and metadata."""

    pil_image: Image.Image
    image_bytes: bytes
    sha256: str
    scan_id: str
    media_type: str
    width: int
    height: int
    original_filename: str


class ForensicAnalyzer:
    """Base class for forensic analyzers."""

    def __init__(self, artifact_base_dir: str = "uploads/artifacts") -> None:
        self.artifact_base_dir = artifact_base_dir

    @property
    def analyzer_id(self) -> str:
        """Unique identifier for this analyzer (e.g., 'metadata', 'ela')."""
        raise NotImplementedError

    def analyze(self, context: ForensicContext) -> ForensicResult:
        """
        Run the analysis and return standardized result.

        Subclasses should implement this and handle their own exceptions,
        returning a ForensicResult with appropriate status and error fields.
        """
        raise NotImplementedError

    def _save_artifact(self, scan_id: str, artifact_name: str, image: Image.Image) -> str:
        """Save an artifact image and return its relative path."""
        import os
        artifact_dir = os.path.join(self.artifact_base_dir, scan_id)
        os.makedirs(artifact_dir, exist_ok=True)
        artifact_path = os.path.join(artifact_dir, artifact_name)
        image.save(artifact_path, "JPEG", quality=95)
        return os.path.relpath(artifact_path, start=".")

    def _create_error_result(self, error_msg: str) -> ForensicResult:
        """Create a standardized error result."""
        return ForensicResult(
            id=self.analyzer_id,
            status="error",
            method="unknown",
            result={},
            interpretation="",
            evidence_category="unknown",
            limitations=[],
            artifact=None,
            error=error_msg,
        )

    def _create_na_result(self, reason: str) -> ForensicResult:
        """Create a 'not applicable' result."""
        return ForensicResult(
            id=self.analyzer_id,
            status="not_applicable",
            method="unknown",
            result={},
            interpretation=reason,
            evidence_category="unknown",
            limitations=[reason],
            artifact=None,
            error=None,
        )