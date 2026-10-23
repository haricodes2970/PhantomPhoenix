"""Comprehensive tests for evidence aggregation, risk scoring, and investigator report building (Phase 2.5)."""

from __future__ import annotations

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from backend.schemas import (
    ModelOutput,
    Indicator,
    VerdictLabel,
    RiskLevel,
    InputDetails,
)
from backend.aggregator import (
    normalize_evidence,
    aggregate_assessment,
    build_investigator_report,
)


class TestEvidenceNormalizationAudit:
    """Test rigorous normalization of evidence items and category mapping."""

    def test_model_inference_normalization(self) -> None:
        model = ModelOutput(
            model_id="test/model",
            model_revision="rev1",
            role="primary",
            status="ok",
            fake_probability=0.92,
            raw_logit=2.45,
            device="cpu",
        )
        items = normalize_evidence([model], [])
        assert len(items) == 1
        item = items[0]
        assert item.source == "ai_detector"
        assert item.evidence_category == "model_inference"
        assert item.status == "ok"
        assert item.result["fake_probability"] == 0.92

    def test_detector_error_normalization(self) -> None:
        model = ModelOutput(
            model_id="test/model",
            model_revision="rev1",
            role="primary",
            status="error",
            fake_probability=None,
        )
        items = normalize_evidence([model], [])
        assert len(items) == 1
        item = items[0]
        assert item.status == "error"
        assert item.evidence_category == "unknown_or_unavailable"

    def test_forensic_indicator_categories(self) -> None:
        ind_computed = Indicator(
            id="metadata",
            method="computed",
            status="present",
            value={"result": {"format": "JPEG"}, "limitations": ["None"]},
            note="Valid metadata",
        )
        ind_heuristic = Indicator(
            id="noise",
            method="heuristic",
            status="ok",
            value={"result": {"noise_std": 12.5}, "limitations": ["Heuristic"]},
            note="Normal noise",
        )
        items = normalize_evidence([], [ind_computed, ind_heuristic])
        assert len(items) == 1 + 2  # 1 detector fallback + 2 indicators

        # Find metadata and noise items
        meta_item = next(i for i in items if i.id == "metadata")
        noise_item = next(i for i in items if i.id == "noise")

        assert meta_item.evidence_category == "computed_observation"
        assert noise_item.evidence_category == "heuristic"


class TestAggregatedAssessmentRules:
    """Test defensible verdict and risk assessment rules."""

    def test_detector_failure_produces_analysis_failed(self) -> None:
        model = ModelOutput(
            model_id="test/model",
            model_revision="rev1",
            role="primary",
            status="error",
            fake_probability=None,
        )
        assessment = aggregate_assessment([model], [], 0.80, 0.20)
        assert assessment.verdict.label == VerdictLabel.ANALYSIS_FAILED
        assert assessment.risk == RiskLevel.UNKNOWN
        assert "Detector unavailable" in assessment.verdict.rationale[0]

    def test_likely_ai_verdict(self) -> None:
        model = ModelOutput(
            model_id="test/model",
            model_revision="rev1",
            role="primary",
            status="ok",
            fake_probability=0.95,
        )
        assessment = aggregate_assessment([model], [], 0.80, 0.20)
        assert assessment.verdict.label == VerdictLabel.LIKELY_AI
        assert assessment.risk == RiskLevel.HIGH

    def test_likely_real_verdict(self) -> None:
        model = ModelOutput(
            model_id="test/model",
            model_revision="rev1",
            role="primary",
            status="ok",
            fake_probability=0.05,
        )
        assessment = aggregate_assessment([model], [], 0.80, 0.20)
        assert assessment.verdict.label == VerdictLabel.LIKELY_REAL
        assert assessment.risk == RiskLevel.LOW

    def test_likely_real_with_anomalies_elevates_risk(self) -> None:
        model = ModelOutput(
            model_id="test/model",
            model_revision="rev1",
            role="primary",
            status="ok",
            fake_probability=0.05,
        )
        ind_noise = Indicator(
            id="noise",
            method="heuristic",
            status="ok",
            value={"result": {"noise_std": 30.0}, "limitations": []},
            note="Elevated noise variance",
        )
        assessment = aggregate_assessment([model], [ind_noise], 0.80, 0.20)
        assert assessment.verdict.label == VerdictLabel.LIKELY_REAL
        assert assessment.risk == RiskLevel.MODERATE
        assert any("Risk elevated to MODERATE" in r for r in assessment.verdict.rationale)

    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (0.05, VerdictLabel.LIKELY_REAL),
            (0.050001, VerdictLabel.INCONCLUSIVE),
            (0.799999, VerdictLabel.INCONCLUSIVE),
            (0.80, VerdictLabel.LIKELY_AI),
            (0.800001, VerdictLabel.LIKELY_AI),
        ],
    )
    def test_active_threshold_boundaries(self, score: float, expected: VerdictLabel) -> None:
        model = ModelOutput(
            model_id="test/model",
            model_revision="rev1",
            role="primary",
            status="ok",
            fake_probability=score,
        )
        assessment = aggregate_assessment([model], [], 0.80, 0.05)
        assert assessment.verdict.label == expected
        assert model.threshold_policy == "0.80 likely_ai / 0.05 likely_real"

    @pytest.mark.parametrize("score", [float("nan"), float("inf"), -0.01, 1.01])
    def test_invalid_probability_produces_analysis_failed(self, score: float) -> None:
        model = ModelOutput(
            model_id="test/model",
            model_revision="rev1",
            role="primary",
            status="ok",
            fake_probability=score,
        )
        assessment = aggregate_assessment([model], [], 0.80, 0.05)
        assert assessment.verdict.label == VerdictLabel.ANALYSIS_FAILED
        assert assessment.risk == RiskLevel.UNKNOWN

    def test_inconclusive_verdict(self) -> None:
        model = ModelOutput(
            model_id="test/model",
            model_revision="rev1",
            role="primary",
            status="ok",
            fake_probability=0.50,
        )
        assessment = aggregate_assessment([model], [], 0.80, 0.05)
        assert assessment.verdict.label == VerdictLabel.INCONCLUSIVE
        assert assessment.risk == RiskLevel.MODERATE


class TestInvestigatorReportAudit:
    """Test six-part investigator report generation and honest status reporting."""

    def test_investigator_report_structure(self) -> None:
        scan_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        input_details = InputDetails(
            sha256="c" * 64,
            filename="audit_test.jpg",
            media_type="image/jpeg",
            byte_size=150000,
            width=800,
            height=600,
        )
        model = ModelOutput(
            model_id="test/model",
            model_revision="rev1",
            role="primary",
            status="ok",
            fake_probability=0.10,
        )
        assessment = aggregate_assessment([model], [], 0.80, 0.20)

        report = build_investigator_report(
            scan_id=scan_id,
            created_at=created_at,
            input_details=input_details,
            models=[model],
            indicators=[],
            verdict=assessment.verdict,
            assessment=assessment,
        )

        assert report.section_1_file_integrity.sha256 == "c" * 64
        assert report.section_2_source_discovery.status == "not_searched"
        assert report.section_3_publisher_intelligence.status == "unknown"
        assert report.section_4_generator_attribution.status == "unsupported"
        assert report.section_5_external_evidence.status == "not_available"
        assert report.section_6_evidence_preservation.scan_identifier == scan_id