# PHANTOM PHOENIX — MILESTONE 2 IMPLEMENTATION PLAN

**Target**: October 20, 2026 Demo  
**Approach**: Incremental, test-driven, honest about limitations

---

## PHASE 2.1 — Repository & Dataset Audit ✅ COMPLETE

**Delivered**: `PHASE_2_AUDIT_REPORT.md`

**Key Findings**:
- 6,000 images verified (3K real, 3K AI), 0 duplicates, clean splits
- Detector: ViT-Small binary classifier, 65.6% accuracy, 32.8% recall @ 0.5
- **Critical**: 0% recall on FLUX, Sora, GPT-Image-2, Seedream (22% of AI test set)
- All unit tests pass (166), DB tests skipped (no PostgreSQL)

---

## PHASE 2.2 — Dataset Expansion (P0) — DEFERRED TO POST-DEMO

**Decision**: Do not force expansion during deadline sprint. Current 6,000 is a valid, documented baseline.

**Post-Demo Target**: 10,000+ with emphasis on FLUX, Sora, GPT-Image-2, Seedream, GAN, editing pipelines.

**Scripts to Maintain** (already exist):
- `scripts/audit_dataset_manifest.py` — count/validate
- `scripts/assign_dataset_splits.py` — reproducible splitting
- `scripts/audit_physical_dataset.py` — corruption check
- `scripts/dataset_quality_audit.py` — quality metrics

---

## PHASE 2.3 — Detector Evaluation & Improvement (P0)

### Current Baseline (Documented)
| Threshold | Accuracy | Precision | Recall | F1 | Notes |
|-----------|----------|-----------|--------|-----|-------|
| 0.50 | 65.6% | 99.4% | 32.8% | 49.3% | Production binary |
| 0.20 | 69.4% | 98.5% | 40.6% | 57.5% | Better recall |
| 0.05 | 75.4% | 97.7% | 53.0% | 68.7% | Validation-selected |

### Action Items (Next 2 Days)

| Task | Owner | Est. Time | Status |
|------|-------|-----------|--------|
| Run OwensLab/commfor-model-384 benchmark on test set | Hari | 2h | Script exists: `benchmark_alternative_detector.py` |
| Compare per-generator recall: OwensLab vs current | Hari | 1h | Use existing generalization audit script |
| If OwensLab improves FLUX/Sora recall → document swap recommendation | Hari | 1h | No model swap in sprint without measured improvement |
| Document: why no fine-tuning in sprint (compute, time, leakage risk) | Hari | 30m | Written in audit report |

**Deliverable**: Updated evaluation comparison in `docs/` or audit report.

---

## PHASE 2.4 — Generator Attribution (P1)

### Current State: NOT IMPLEMENTED
- Detector only outputs binary `fake_probability`
- No attribution labels, no model, no training data

### Sprint Goal: Service Contract + Honest UNKNOWN

**Implementation**:
```
backend/attribution/
  __init__.py           # Exports AttributionService, AttributionResult
  service.py            # Interface + UNKNOWN implementation
  schemas.py            # AttributionResult, CandidateFamily
  models/               # (empty - placeholder for future model)
```

**API Contract** (add to `ScanResult`):
```python
class AttributionResult(BaseModel):
    status: Literal["ok", "unsupported", "error"]
    method: Literal["model_inference", "provenance", "unknown"]
    candidates: list[CandidateFamily] = []
    limitations: list[str] = []
    
class CandidateFamily:
    family: str           # "stable-diffusion", "flux", "midjourney", "dalle", "gan", "unknown"
    confidence: float     # 0-1 (NOT calibrated probability)
    evidence_type: str    # "model_inference" | "verified_provenance"
```

**Behavior**:
- `status="unsupported"` → `candidates=[]`, `limitations=["Generator attribution not available in this deployment"]`
- Never invent family names
- Distinguish `model_inference` from `verified_provenance`

**Tests**:
- `test_attribution_service_returns_unsupported.py`
- `test_attribution_schema_validation.py`

**Effort**: 2-3 hours

---

## PHASE 2.5 — Forensic Explainability (P0/P1)

### Current State
- ViT attention available via `output_attentions=True`
- Attention rollout metrics computed (entropy, CLS-to-patch mean/max)
- **No spatial heatmap (Grad-CAM) generated or saved as artifact**

### Sprint Goal: Grad-CAM Heatmap Artifact

**Implementation**:
1. In `detector.py._run_inference()`: Compute Grad-CAM from last-layer attention
2. Save as `gradcam.jpg` artifact (overlay on original image)
3. Add to `explainability.artifact` in `ModelOutput`
4. Include in PDF report under "Forensic Artifact Visualizations"

**Technical Approach**:
```python
# From last-layer attention: [num_heads, seq_len, seq_len]
# CLS token attends to patches → spatial map
# Upsample to image resolution, overlay as heatmap
```

**Tests**:
- `test_gradcam_artifact_generated.py`
- `test_gradcam_included_in_report.py`

**Effort**: 3-4 hours

---

## PHASE 2.6 — Six-Part Investigator Evidence Report (P0)

### Current Report Sections (3 of 6)
1. ✅ Executive Summary / Verdict
2. ✅ Image Properties  
3. ✅ AI Detector Inference
4. ✅ Verdict Rationale & Limitations
5. ✅ Forensic Indicators & Evidence
6. ✅ Forensic Artifact Visualizations

### Required 6 Sections (Per Spec)

| Section | Title | Current Status | Sprint Action |
|---------|-------|----------------|---------------|
| 1 | File Integrity & Provenance | ✅ Partial (SHA-256, props, metadata) | Enhance: add integrity status, scan ID, timestamp |
| 2 | Source Discovery | ❌ Missing | Add placeholder: "NOT SEARCHED" |
| 3 | Publisher & Account Intelligence | ❌ Missing | Add placeholder: "UNKNOWN" |
| 4 | Generator & Editing Attribution | ❌ Missing | Add placeholder: "UNSUPPORTED" or real attribution |
| 5 | External Investigation Evidence | ❌ Missing | Add placeholder: "NOT AVAILABLE" |
| 6 | Evidence Preservation & Corroboration | ⚠️ Partial | Enhance: add audit events, chain of custody, detector versions |

### Implementation Plan

**Backend Schema Extensions** (`backend/schemas.py`):
```python
class SourceDiscovery(BaseModel):
    status: Literal["searched", "not_searched", "error"]
    candidate_urls: list[str] = []
    match_strength: str | None = None  # "exact", "near", "none"
    earliest_known: str | None = None
    limitations: list[str] = []

class PublisherIntelligence(BaseModel):
    status: Literal["identified", "unknown", "not_searched", "error"]
    account_name: str | None = None
    source_url: str | None = None
    relationship: str | None = None
    verification_status: str | None = None

class GeneratorAttribution(BaseModel):  # Reuse from Phase 2.4
    ...

class ExternalInvestigationEvidence(BaseModel):
    status: Literal["available", "not_available", "not_authorized", "error"]
    platform_records: list[dict] = []
    publication_timestamps: list[str] = []
    limitations: list[str] = []

class EvidencePreservation(BaseModel):
    original_hash: str
    scan_id: str
    analysis_timestamp: str
    detector_version: str
    forensic_versions: dict[str, str]
    audit_events: list[dict] = []
    corroboration_status: str
    outstanding_questions: list[str] = []
```

**Report Template Update** (`backend/report.py`):
- Add 6 section headers in fixed order
- For missing sections: render "STATUS: NOT SEARCHED / UNKNOWN / NOT AVAILABLE"
- Never hide missing capabilities

**Effort**: 4-5 hours

---

## PHASE 2.7 — Evidence Aggregation, Risk & Verdict (P0)

### Current State
- Threshold-based verdict (0.80/0.20)
- Risk: HIGH/MODERATE/LOW/UNKNOWN
- Heuristic anomaly counting (ELA, noise)

### Required Enhancements

| Enhancement | Description | Effort |
|-------------|-------------|--------|
| Document risk dimensions | AI likelihood, manipulation evidence, provenance confidence, investigative risk, evidence completeness | 1h |
| Formalize scoring logic | Write `docs/RISK_SCORING.md` with formulas/thresholds | 1h |
| Surface contradictory signals | e.g., low AI score but high ELA anomaly → flag in rationale | 1h |
| Prevent double-counting | Correlated indicators (ELA + noise on same region) not independent | 1h |
| INCONCLUSIVE behavior | Ensure insufficient evidence → INCONCLUSIVE, not LIKELY_REAL | 30m |

**Tests**: Add edge-case tests for contradictory signals, missing evidence.

**Effort**: 3-4 hours

---

## PHASE 2.8 — Backend & PDF Integration (P0)

### Integration Checklist

- [ ] Extend `ScanResult` with 6-section evidence objects
- [ ] Extend `Scan` model (SQLAlchemy) with JSONB columns for new sections
- [ ] Update `ScanRepository.create()` to persist new fields
- [ ] Update `Scan.to_scan_result()` to include new sections
- [ ] Update `generate_scan_pdf()` with 6-section template
- [ ] Add regression tests: existing AI report, existing real report, new sections
- [ ] Verify database persistence + retrieval round-trip

**Effort**: 3-4 hours

---

## PHASE 2.9 — October 20 Release Candidate (P0)

### Freeze Date: October 18 EOD

### Validation Checklist

| Check | Command | Expected |
|-------|---------|----------|
| Unit tests | `PYTHONPATH=. .venv/bin/pytest tests/ -x` | 166+ passed |
| DB integration | `RUN_DB_TESTS=1 PYTHONPATH=. .venv/bin/pytest tests/test_database.py` | 9 passed |
| E2E smoke | `RUN_E2E=1 npx playwright test` (in frontend) | 4 passed |
| Report generation | Manual: upload AI image → download PDF | 6 sections render |
| Report generation | Manual: upload real image → download PDF | 6 sections render |
| Attribution service | Unit test: returns UNKNOWN | Pass |
| Grad-CAM artifact | Unit test: artifact exists in report | Pass |
| Security scan | `grep -r "secret\|password\|token" --include="*.py" backend/ | grep -v test` | No hardcoded secrets |
| Lint | `cd frontend && npm run lint` | No errors |

### Demo Deliverables

- [ ] Working integrated MVP (upload → report)
- [ ] Sample AI report (6 sections, Grad-CAM, attribution=UNSUPPORTED)
- [ ] Sample Real report (6 sections, Grad-CAM, attribution=UNSUPPORTED)
- [ ] Dataset audit metrics (this report)
- [ ] Known limitations document
- [ ] Completed/Incomplete feature matrix
- [ ] Demonstration checklist

---

## DAILY EXECUTION SCHEDULE

### Day 1 (Oct 19) — Core Backend Features

| Time | Task |
|------|------|
| 09:00-11:00 | Implement Attribution Service (Phase 2.4) |
| 11:00-13:00 | Implement Grad-CAM Heatmap (Phase 2.5) |
| 13:00-14:00 | Lunch |
| 14:00-17:00 | Six-Part Report Schema + PDF Template (Phase 2.6) |
| 17:00-18:00 | Run OwensLab benchmark (Phase 2.3) |

### Day 2 (Oct 20) — Integration & Validation

| Time | Task |
|------|------|
| 09:00-11:00 | Risk Scoring Documentation (Phase 2.7) |
| 11:00-13:00 | Backend Integration + DB Persistence (Phase 2.8) |
| 13:00-14:00 | Lunch |
| 14:00-16:00 | Full Test Suite + Regression Tests |
| 16:00-17:00 | Generate Sample Reports (AI + Real) |
| 17:00-18:00 | Documentation Update + Demo Checklist |

---

## DECISION LOG

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-10-19 | Defer dataset expansion to post-demo | 6,000 is valid baseline; expansion needs licensing review |
| 2026-10-19 | No model swap without measured improvement | OwensLab benchmark exists; will evaluate but not swap blindly |
| 2026-10-19 | Attribution = UNKNOWN in sprint | No defensible model; honest placeholder better than fake |
| 2026-10-19 | Six-section report with placeholders | Demo requirement; honest about missing capabilities |
| 2026-10-19 | Grad-CAM from existing ViT attention | Uses loaded model; no new dependencies |

---

## SUCCESS CRITERIA FOR OCT 20 DEMO

| Criterion | Minimum Bar |
|-----------|-------------|
| Upload image → PDF report | Works end-to-end |
| Report has 6 sections | All 6 render (3 real, 3 placeholders) |
| Grad-CAM artifact visible | In "Forensic Artifact Visualizations" |
| Attribution shows "UNSUPPORTED" | Section 4 renders with honest status |
| No fabricated data | All UNKNOWN/NOT SEARCHED explicit |
| Tests pass | 166+ unit, 9 DB, 4 E2E |
| Known limitations documented | In report footer and demo checklist |

---

*This plan is executable by a single engineer. No frontend changes. API compatible. All new code tested.*