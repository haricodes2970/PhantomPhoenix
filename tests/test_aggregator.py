"""Tests for the evidence aggregator edge cases."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from backend.schemas import ModelOutput, Indicator, VerdictLabel, RiskLevel
from backend.aggregator import normalize_evidence, aggregate_assessment


def create_mock_model(fake_prob: float, status: str = "ok") -> ModelOutput:
    return ModelOutput(
        model_id="test-model",
        model_revision="test-revision",
        role="primary",
        status=status,
        fake_probability=fake_prob,
        raw_logit=0.0,
        threshold_policy="0.80 likely_ai / 0.05 likely_real",
        limitations=["test limitation"],
        device="cpu",
        duration_seconds=0.1,
    )


def create_mock_indicator(ind_id: str, method: str = "computed", evidence_cat: str = "computed") -> Indicator:
    return Indicator(
        id=ind_id,
        method=method,
        status="ok",
        value={
            "result": {"test_value": 1.0},
            "evidence_category": evidence_cat,
            "limitations": ["test limitation"],
            "error": None,
        },
        note="Test interpretation",
        artifact=None,
    )


class TestNormalizeEvidence:
    """Tests for normalize_evidence function."""

    def test_normalizes_detector_output(self) -> None:
        """Test that detector output is normalized correctly."""
        models = [create_mock_model(0.9)]
        indicators = []
        items = normalize_evidence(models, indicators)

        assert len(items) == 1
        item = items[0]
        assert item.id == "test-model"
        assert item.source == "ai_detector"
        assert item.method == "model_inference"
        assert item.evidence_category == "model_inference"
        assert item.result["fake_probability"] == 0.9
        assert "AI detector" in item.interpretation

    def test_handles_detector_error(self) -> None:
        """Test that detector errors are normalized correctly."""
        models = [create_mock_model(0.5, status="error")]
        indicators = []
        items = normalize_evidence(models, indicators)

        assert len(items) == 1
        item = items[0]
        assert item.status == "error"
        assert item.evidence_category == "unknown_or_unavailable"
        assert "assigned a fake probability of 0.5000" in item.interpretation

    def test_normalizes_forensic_indicators(self) -> None:
        """Test that forensic indicators are normalized correctly."""
        models = [create_mock_model(0.5)]
        indicators = [
            create_mock_indicator("metadata", "computed", "computed"),
            create_mock_indicator("ela", "computed", "computed"),
            create_mock_indicator("noise", "heuristic", "heuristic"),
            create_mock_indicator("frequency", "computed", "computed"),
        ]
        items = normalize_evidence(models, indicators)

        assert len(items) == 5  # 1 detector + 4 forensic
        ids = {item.id for item in items}
        assert ids == {"test-model", "metadata", "ela", "noise", "frequency"}

    def test_evidence_category_mapping(self) -> None:
        """Test that method maps to correct evidence category."""
        models = [create_mock_model(0.5)]
        indicators = [
            Indicator(id="metadata", method="computed", status="ok", value={"result": {}, "evidence_category": "computed", "limitations": [], "error": None}, note="test"),
            Indicator(id="noise", method="heuristic", status="ok", value={"result": {}, "evidence_category": "heuristic", "limitations": [], "error": None}, note="test"),
        ]
        items = normalize_evidence(models, indicators)

        forensic_items = [i for i in items if i.source.startswith("forensic_")]
        assert any(i.evidence_category == "computed_observation" for i in forensic_items if i.id == "metadata")
        assert any(i.evidence_category == "heuristic" for i in forensic_items if i.id == "noise")


class TestAggregateAssessment:
    """Tests for aggregate_assessment function."""

    def test_detector_error_returns_analysis_failed(self) -> None:
        """Detector errors should produce ANALYSIS_FAILED."""
        models = [create_mock_model(0.5, status="error")]
        indicators = []
        result = aggregate_assessment(models, indicators, 0.8, 0.2)

        assert result.verdict.label == VerdictLabel.ANALYSIS_FAILED
        assert result.risk == RiskLevel.UNKNOWN
        assert "Detector unavailable" in result.verdict.rationale[0]

    def test_no_primary_detector_returns_analysis_failed(self) -> None:
        """Missing primary detector should produce ANALYSIS_FAILED."""
        models = []
        indicators = []
        result = aggregate_assessment(models, indicators, 0.8, 0.2)

        assert result.verdict.label == VerdictLabel.ANALYSIS_FAILED
        assert result.risk == RiskLevel.UNKNOWN

    def test_high_fake_probability_returns_likely_ai(self) -> None:
        """High fake probability should produce LIKELY_AI with HIGH risk."""
        models = [create_mock_model(0.95)]
        indicators = []
        result = aggregate_assessment(models, indicators, 0.8, 0.2)

        assert result.verdict.label == VerdictLabel.LIKELY_AI
        assert result.risk == RiskLevel.HIGH
        assert any("LIKELY_AI" in r and "0.95" in r for r in result.verdict.rationale)

    def test_low_fake_probability_returns_likely_real(self) -> None:
        """Low fake probability should produce LIKELY_REAL with LOW risk."""
        models = [create_mock_model(0.1)]
        indicators = []
        result = aggregate_assessment(models, indicators, 0.8, 0.2)

        assert result.verdict.label == VerdictLabel.LIKELY_REAL
        assert result.risk == RiskLevel.LOW
        assert any("LIKELY_REAL" in r and "0.10" in r for r in result.verdict.rationale)

    def test_mid_fake_probability_returns_inconclusive(self) -> None:
        """Mid-range fake probability should produce INCONCLUSIVE."""
        models = [create_mock_model(0.5)]
        indicators = []
        result = aggregate_assessment(models, indicators, 0.8, 0.2)

        assert result.verdict.label == VerdictLabel.INCONCLUSIVE
        assert result.risk == RiskLevel.MODERATE
        assert any("INCONCLUSIVE" in r and "0.50" in r for r in result.verdict.rationale)

    def test_likely_real_with_heuristic_anomalies_elevates_risk(self) -> None:
        """LIKELY_REAL with heuristic anomalies should elevate risk to MODERATE."""
        models = [create_mock_model(0.1)]
        indicators = [
            create_mock_indicator("noise", "heuristic", "heuristic"),
        ]
        # Modify the noise indicator to have high noise
        indicators[0].value = {
            "result": {"noise_std": 30.0},
            "evidence_category": "heuristic",
            "limitations": [],
            "error": None,
        }

        result = aggregate_assessment(models, indicators, 0.8, 0.2)

        assert result.verdict.label == VerdictLabel.LIKELY_REAL
        assert result.risk == RiskLevel.MODERATE
        assert any("Risk elevated to MODERATE" in r for r in result.verdict.rationale)

    def test_not_claimed_includes_standard_items(self) -> None:
        """Not claimed should include standard disclaimers."""
        models = [create_mock_model(0.5)]
        indicators = []
        result = aggregate_assessment(models, indicators, 0.8, 0.2)

        not_claimed = result.verdict.not_claimed
        assert "generator identity" in not_claimed
        assert "localized forgery without verified provenance" in not_claimed
        assert "calibrated real-world criminal fraud probability" in not_claimed