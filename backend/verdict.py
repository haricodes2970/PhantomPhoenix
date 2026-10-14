"""Verdict policy - deterministic rules from model outputs."""

from __future__ import annotations

from backend.schemas import Verdict, VerdictLabel, RiskLevel, ModelOutput


def determine_verdict(
    model_outputs: list[ModelOutput],
    likely_ai_threshold: float,
    likely_real_threshold: float,
) -> Verdict:
    """
    Determine final verdict from model outputs.

    Rules:
    - Any detector error -> ANALYSIS_FAILED (never LIKELY_REAL)
    - If primary model fake_prob >= likely_ai_threshold -> LIKELY_AI
    - If primary model fake_prob <= likely_real_threshold -> LIKELY_REAL
    - Otherwise -> INCONCLUSIVE
    - Missing model output -> INCONCLUSIVE
    """
    # Check for detector errors first
    primary = next((m for m in model_outputs if m.role == "primary"), None)

    if primary is None or primary.status != "ok" or primary.fake_probability is None:
        return Verdict(
            label=VerdictLabel.ANALYSIS_FAILED,
            risk=RiskLevel.UNKNOWN,
            rationale=["Detector unavailable or failed to produce a score"],
            not_claimed=[
                "generator identity",
                "legal authenticity",
                "localized forgery",
                "calibrated confidence",
            ],
        )

    score = primary.fake_probability

    if score >= likely_ai_threshold:
        return Verdict(
            label=VerdictLabel.LIKELY_AI,
            risk=RiskLevel.HIGH,
            rationale=[f"Primary fake probability {score:.4f} >= {likely_ai_threshold}"],
            not_claimed=[
                "generator identity",
                "legal authenticity",
                "localized forgery",
                "calibrated confidence - provisional screening thresholds only",
            ],
        )

    if score <= likely_real_threshold:
        return Verdict(
            label=VerdictLabel.LIKELY_REAL,
            risk=RiskLevel.LOW,
            rationale=[f"Primary fake probability {score:.4f} <= {likely_real_threshold}"],
            not_claimed=[
                "generator identity",
                "legal authenticity - missing metadata is not evidence of generation",
                "localized forgery",
                "calibrated confidence - provisional screening thresholds only",
            ],
        )

    return Verdict(
        label=VerdictLabel.INCONCLUSIVE,
        risk=RiskLevel.MODERATE,
        rationale=[
            f"Primary fake probability {score:.4f} between thresholds "
            f"({likely_real_threshold} - {likely_ai_threshold})"
        ],
        not_claimed=[
            "generator identity",
            "legal authenticity",
            "localized forgery",
            "calibrated confidence - provisional screening thresholds only",
        ],
    )