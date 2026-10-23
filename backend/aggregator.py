"""Evidence aggregation and defensible verdict engine."""

from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any
from pydantic import BaseModel, Field

from backend.schemas import (
    ModelOutput,
    Indicator,
    Verdict,
    VerdictLabel,
    RiskLevel,
    NormalizedEvidenceItem,
    InputDetails,
    InvestigatorEvidenceReport,
    FileIntegrityProvenance,
    SourceDiscovery,
    PublisherIntelligence,
    GeneratorAttribution,
    ExternalInvestigationEvidence,
    EvidencePreservation,
)
from backend.attribution import get_attribution_service, AttributionStatus


class AggregatedAssessment(BaseModel):
    """Complete aggregated evidence assessment."""

    evidence_items: list[NormalizedEvidenceItem] = Field(default_factory=list)
    verdict: Verdict
    risk: RiskLevel
    summary: str = ""


def normalize_evidence(models: list[ModelOutput], indicators: list[Indicator]) -> list[NormalizedEvidenceItem]:
    """Normalize detector and forensic outputs into standardized evidence items."""
    items: list[NormalizedEvidenceItem] = []

    # 1. Normalize AI detector output
    primary = next((m for m in models if m.role == "primary"), None)
    if primary:
        status = "ok" if primary.status == "ok" and primary.fake_probability is not None else "error"
        cat = "model_inference" if status == "ok" else "unknown_or_unavailable"
        items.append(
            NormalizedEvidenceItem(
                id=primary.model_id,
                source="ai_detector",
                method="model_inference",
                status=status,
                evidence_category=cat,
                result={
                    "fake_probability": primary.fake_probability,
                    "raw_logit": primary.raw_logit,
                    "device": primary.device,
                },
                interpretation=(
                    f"AI detector (ViT-Small) assigned a fake probability of {primary.fake_probability:.4f}."
                    if primary.fake_probability is not None
                    else "AI detector failed to produce a valid score."
                ),
                limitations=primary.limitations,
                artifact=None,
            )
        )
    else:
        items.append(
            NormalizedEvidenceItem(
                id="primary_detector",
                source="ai_detector",
                method="model_inference",
                status="error",
                evidence_category="unknown_or_unavailable",
                result={},
                interpretation="No primary AI detector output was produced.",
                limitations=["Detector unavailable"],
                artifact=None,
            )
        )

    # 2. Normalize forensic indicators
    for ind in indicators:
        val = ind.value or {}
        res = val.get("result", {})
        lim = val.get("limitations", [])
        err = val.get("error")

        # Determine evidence category
        if ind.status == "error" or err:
            cat = "unknown_or_unavailable"
        elif ind.method == "heuristic":
            cat = "heuristic"
        elif ind.method == "computed":
            cat = "computed_observation"
        elif ind.method == "verified":
            cat = "verified_evidence"
        else:
            cat = "unknown_or_unavailable"

        source_map = {
            "metadata": "forensic_metadata",
            "ela": "forensic_ela",
            "noise": "forensic_noise",
            "frequency": "forensic_frequency",
        }

        items.append(
            NormalizedEvidenceItem(
                id=ind.id,
                source=source_map.get(ind.id, f"forensic_{ind.id}"),
                method=ind.method,
                status=ind.status,
                evidence_category=cat,
                result=res if isinstance(res, dict) else {"data": res},
                interpretation=ind.note,
                limitations=lim if isinstance(lim, list) else [str(lim)],
                artifact=ind.artifact,
            )
        )

    return items


def aggregate_assessment(
    models: list[ModelOutput],
    indicators: list[Indicator],
    likely_ai_threshold: float,
    likely_real_threshold: float,
) -> AggregatedAssessment:
    """
    Aggregate evidence and determine defensible verdict and risk.

    Rules:
    - AI generation assessment and manipulation indicators remain strictly separated.
    - Detector failure -> ANALYSIS_FAILED (never LIKELY_REAL), Risk: UNKNOWN.
    - AI Score >= likely_ai_threshold -> LIKELY_AI, Risk: HIGH.
    - AI Score <= likely_real_threshold -> LIKELY_REAL, Risk: LOW (unless severe heuristic anomalies raise risk to MODERATE).
    - Otherwise -> INCONCLUSIVE, Risk: MODERATE.
    - Every rationale must trace to actual normalized evidence items.
    """
    evidence_items = normalize_evidence(models, indicators)

    primary = next((m for m in models if m.role == "primary"), None)

    # 1. Check detector status / errors
    if primary is None or primary.status != "ok" or primary.fake_probability is None:
        verdict = Verdict(
            label=VerdictLabel.ANALYSIS_FAILED,
            risk=RiskLevel.UNKNOWN,
            rationale=["Detector unavailable or failed to produce a score (Model inference error)"],
            not_claimed=[
                "generator identity",
                "legal authenticity",
                "localized forgery",
                "calibrated confidence",
            ],
        )
        return AggregatedAssessment(
            evidence_items=evidence_items,
            verdict=verdict,
            risk=RiskLevel.UNKNOWN,
            summary="Analysis failed due to detector unavailability or inference failure.",
        )

    score = primary.fake_probability
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        verdict = Verdict(
            label=VerdictLabel.ANALYSIS_FAILED,
            risk=RiskLevel.UNKNOWN,
            rationale=["Detector produced an invalid probability score"],
            not_claimed=[
                "generator identity",
                "legal authenticity",
                "localized forgery",
                "calibrated confidence",
            ],
        )
        return AggregatedAssessment(
            evidence_items=evidence_items,
            verdict=verdict,
            risk=RiskLevel.UNKNOWN,
            summary="Analysis failed because detector probability was invalid.",
        )

    rationales: list[str] = []

    # Trace AI model evidence
    rationales.append(f"AI model inference: primary fake probability {score:.4f} (thresholds: >= {likely_ai_threshold} LIKELY_AI, <= {likely_real_threshold} LIKELY_REAL).")

    # Check heuristic anomaly count
    heuristic_anomalies = 0
    for item in evidence_items:
        if item.evidence_category == "heuristic" and item.status == "ok":
            # Check if values indicate high anomaly
            if item.id == "noise":
                std = item.result.get("noise_std", 0)
                if std > 25.0:  # arbitrary heuristic threshold for high noise variance
                    heuristic_anomalies += 1
                    rationales.append(f"Heuristic noise indicator ({item.id}) shows elevated noise variance (std {std:.2f}).")
            elif item.id == "ela":
                mean_diff = item.result.get("mean_difference", 0)
                if mean_diff > 15.0:  # arbitrary heuristic threshold for high ELA residual
                    heuristic_anomalies += 1
                    rationales.append(f"Heuristic ELA indicator ({item.id}) shows elevated recompression residual (mean {mean_diff:.2f}).")

    # Determine Verdict Label
    if score >= likely_ai_threshold:
        label = VerdictLabel.LIKELY_AI
        risk = RiskLevel.HIGH
        rationales.insert(0, f"Verdict LIKELY_AI: fake probability {score:.4f} meets or exceeds LIKELY_AI threshold ({likely_ai_threshold}).")
    elif score <= likely_real_threshold:
        label = VerdictLabel.LIKELY_REAL
        # If real score but heuristic anomalies present, elevate risk to moderate
        if heuristic_anomalies > 0:
            risk = RiskLevel.MODERATE
            rationales.append(f"Risk elevated to MODERATE due to {heuristic_anomalies} heuristic compression/noise anomaly indicators, despite low AI score.")
        else:
            risk = RiskLevel.LOW
        rationales.insert(0, f"Verdict LIKELY_REAL: fake probability {score:.4f} is at or below LIKELY_REAL threshold ({likely_real_threshold}).")
    else:
        label = VerdictLabel.INCONCLUSIVE
        risk = RiskLevel.MODERATE
        rationales.insert(0, f"Verdict INCONCLUSIVE: fake probability {score:.4f} falls in the ambiguous zone ({likely_real_threshold} - {likely_ai_threshold}).")

    not_claimed = [
        "generator identity",
        "legal authenticity - missing metadata or noise patterns are not proof of editing",
        "localized forgery without verified provenance",
        "calibrated real-world criminal fraud probability",
    ]

    verdict = Verdict(
        label=label,
        risk=risk,
        rationale=rationales,
        not_claimed=not_claimed,
    )

    summary = (
        f"Assessment completed with verdict {label.value} and risk level {risk.value}. "
        f"Evaluated 1 model inference and {len(indicators)} forensic indicator(s)."
    )

    return AggregatedAssessment(
        evidence_items=evidence_items,
        verdict=verdict,
        risk=risk,
        summary=summary,
    )


def build_investigator_report(
    scan_id: str,
    created_at: str,
    input_details: InputDetails,
    models: list[ModelOutput],
    indicators: list[Indicator],
    verdict: Verdict,
    assessment: AggregatedAssessment,
) -> InvestigatorEvidenceReport:
    """
    Build the six-part investigator evidence report from scan data.

    Each section explicitly states its status (searched/not_searched/unknown/etc.)
    to maintain honest reporting of capabilities.
    """
    primary = next((m for m in models if m.role == "primary"), None)
    fake_prob = primary.fake_probability if primary else None
    detector_model = primary.model_id if primary else "unknown"
    detector_revision = primary.model_revision if primary else "unknown"

    # Section 1: File Integrity & Provenance
    exif_fields = {}
    missing_meta = []
    xmp_present = False
    for ind in indicators:
        if ind.id == "metadata" and ind.status == "ok":
            res = ind.value.get("result", {}) if isinstance(ind.value, dict) else {}
            exif_fields = res.get("exif_sample", {})
            xmp_present = res.get("info_tags", {}).get("xmp_present") == "True"
            if not res.get("has_exif", True):
                missing_meta.append("EXIF metadata absent")
            if not xmp_present:
                missing_meta.append("XMP metadata not present")
            break

    section_1 = FileIntegrityProvenance(
        sha256=input_details.sha256,
        original_filename=input_details.filename,
        internal_identifier=str(scan_id),
        file_format=input_details.media_type,
        dimensions=f"{input_details.width} x {input_details.height} px",
        file_size_bytes=input_details.byte_size,
        exif_fields=exif_fields,
        xmp_present=xmp_present,
        missing_metadata_observations=missing_meta,
        integrity_status="verified",
        provenance_status="unknown",
        scan_id=str(scan_id),
        analysis_timestamp_utc=created_at,
    )

    # Section 2: Source Discovery (NOT SEARCHED in current deployment)
    section_2 = SourceDiscovery(
        status="not_searched",
        candidate_urls=[],
        match_method=None,
        match_strength="unknown",
        supporting_evidence=[],
        publication_timestamps=[],
        earliest_known_source=False,
        limitations=[
            "Reverse image search / source discovery not implemented in this deployment.",
            "No integration with search engines or image registries.",
        ],
    )

    # Section 3: Publisher Intelligence (UNKNOWN in current deployment)
    section_3 = PublisherIntelligence(
        status="unknown",
        account_name=None,
        source_url=None,
        relationship=None,
        verification_status="unknown",
        limitations=[
            "Publisher/account intelligence not implemented in this deployment.",
            "No integration with platform APIs or account verification services.",
            "An uploader is not automatically the original creator.",
        ],
    )

    # Section 4: Generator Attribution
    attr_service = get_attribution_service()
    attr_result = attr_service.attribute(None)  # Image not needed for unsupported path
    section_4 = GeneratorAttribution(
        status=attr_result.status,
        method=attr_result.method,
        candidates=[
            {
                "family": c.family,
                "confidence": c.confidence,
                "evidence_type": c.evidence_type,
                "metadata": c.metadata,
            }
            for c in attr_result.candidates
        ],
        limitations=attr_result.limitations,
        error=attr_result.error,
    )

    # Section 5: External Investigation Evidence (NOT AVAILABLE)
    section_5 = ExternalInvestigationEvidence(
        status="not_available",
        platform_records=[],
        publication_timestamps=[],
        public_urls=[],
        account_records=[],
        network_audit_evidence=[],
        source=None,
        retrieval_time_utc=None,
        access_limitations=[
            "External investigation evidence requires authorized access to platform records.",
            "No authorized data sources configured in this deployment.",
        ],
        verification_status="unknown",
    )

    # Section 6: Evidence Preservation & Corroboration
    forensic_versions = {
        "metadata": "1.0",
        "ela": "1.0",
        "noise": "1.0",
        "frequency": "1.0",
    }
    artifact_refs = []
    for ind in indicators:
        if ind.artifact:
            artifact_refs.append(f"{ind.id}: {ind.artifact}")

    section_6 = EvidencePreservation(
        original_file_hash=input_details.sha256,
        scan_identifier=str(scan_id),
        analysis_timestamp_utc=created_at,
        detector_version=f"{detector_model}@{detector_revision}",
        forensic_versions=forensic_versions,
        supporting_observations=[
            f"AI detector fake probability: {fake_prob:.4f}" if fake_prob is not None else "AI detector: unavailable"
        ] + [ind.note for ind in indicators if ind.note],
        artifact_references=artifact_refs,
        evidence_relationships=[
            "AI generation assessment and manipulation indicators evaluated separately",
            "Heuristic indicators (ELA, noise) not used as primary authenticity evidence",
        ],
        audit_events=[],  # Would be populated from audit trail in production
        integrity_checks=[
            "SHA-256 hash verified at upload",
            "Image decoded and validated before analysis",
        ],
        corroboration_status="unverified",
        outstanding_questions=[
            "Generator attribution not available",
            "Source discovery not performed",
            "Publisher identity not established",
            "External investigation evidence not accessible",
        ],
    )

    return InvestigatorEvidenceReport(
        section_1_file_integrity=section_1,
        section_2_source_discovery=section_2,
        section_3_publisher_intelligence=section_3,
        section_4_generator_attribution=section_4,
        section_5_external_evidence=section_5,
        section_6_evidence_preservation=section_6,
    )