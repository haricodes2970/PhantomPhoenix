"""Runner to execute all forensic analyzers and map results to API Indicator schemas."""

from __future__ import annotations

import io
from backend.forensics import ForensicContext, ForensicResult
from backend.forensics.metadata import MetadataAnalyzer
from backend.forensics.ela import ElaAnalyzer
from backend.forensics.noise import NoiseAnalyzer
from backend.forensics.frequency import FrequencyAnalyzer
from backend.image_utils import ValidatedImage
from backend.schemas import Indicator


def run_all_analyzers(validated: ValidatedImage, scan_id: str) -> list[Indicator]:
    """Run all forensic analyzers and return list of Indicator schemas."""
    context = ForensicContext(
        pil_image=validated.pil_image,
        image_bytes=b"",  # Can be populated if needed
        sha256=validated.sha256,
        scan_id=str(scan_id),
        media_type=validated.media_type,
        width=validated.width,
        height=validated.height,
        original_filename=validated.original_filename,
    )

    analyzers = [
        MetadataAnalyzer(),
        ElaAnalyzer(),
        NoiseAnalyzer(),
        FrequencyAnalyzer(),
    ]

    indicators: list[Indicator] = []

    for analyzer in analyzers:
        try:
            res: ForensicResult = analyzer.analyze(context)
            indicators.append(
                Indicator(
                    id=res.id,
                    method=res.method,
                    status=res.status,
                    value={
                        "result": res.result,
                        "evidence_category": res.evidence_category,
                        "limitations": res.limitations,
                        "error": res.error,
                    },
                    note=res.interpretation,
                    artifact=res.artifact,
                )
            )
        except Exception as exc:
            indicators.append(
                Indicator(
                    id=analyzer.analyzer_id,
                    method="unknown",
                    status="error",
                    value={"error": str(exc)},
                    note=f"Analyzer failed: {exc}",
                    artifact=None,
                )
            )

    return indicators