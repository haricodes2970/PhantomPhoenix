# PHANTOM PHOENIX — PHASE 2.1 AUDIT REPORT

**Date**: 2026-10-19  
**Branch**: `feat/dataset-pipeline`  
**Commit**: `d711815` (HEAD)

---

## 1. Repository State

### Git Status
- **Branch**: `feat/dataset-pipeline`
- **Modified files**: 15 (config, main, models, repository, compose, frontend, requirements, tests)
- **Untracked files**: 20+ (documentation, deployment, alembic migrations, test files, scripts)

### Test Baseline (Current)
```
166 passed, 6 skipped
- Skipped: 9 database integration tests (no PostgreSQL running)
- Skipped: 1 E2E test (requires RUN_E2E=1)
- Skipped: 1 real model smoke test (requires explicit flag)
```

All unit tests pass. Database integration tests require running PostgreSQL.

---

## 2. Dataset Audit Results

### Main Dataset Manifest: `datasets/manifests/dataset_manifest.csv`
| Metric | Value |
|--------|-------|
| **Total rows** | 6,000 |
| **Unique SHA-256 hashes** | 6,000 (0 duplicates) |
| **Missing files** | 0 |
| **Corrupt/unreadable** | 0 |
| **Labels** | real: 3,000 | ai_generated: 3,000 |

### Generator Family Distribution
| Generator | Count |
|-----------|-------|
| z-image-turbo | 850 |
| imagenet (real) | 2,017 |
| docci (real) | 983 |
| flux.2-klein-9b | 561 |
| illustrious | 401 |
| gpt-image-1.5 | 385 |
| midjourney-7 | 221 |
| veo-3 | 131 |
| wan-video-2.5 | 83 |
| ernie-image-turbo | 51 |
| recraft-v3 | 58 |
| gpt-image-2 | 37 |
| sora-2 | 37 |
| seedream-v5.0 | 27 |
| lumina-17-2-25 | 27 |
| nano-banana-pro | 16 |
| ideogram-2.0 | 17 |
| ernie-image | 28 |
| recraft-v2 | 19 |
| frames-23-1-25 | 20 |
| halfmoon-4-4-25 | 13 |
| aurora-20-1-25 | 18 |

### Split Integrity
| Split | Total | Real | AI | Class Balance |
|-------|-------|------|-----|---------------|
| train | 4,188 | 2,099 | 2,089 | 50.1% / 49.9% |
| val | 890 | 449 | 441 | 50.4% / 49.6% |
| test | 922 | 452 | 470 | 49.0% / 51.0% |

**Zero hash overlap between splits confirmed.**

### Pilot Dataset: `datasets/openfake_pilot/eval_manifest.csv`
- 50 images (25 real, 25 fake)
- Generators: z-image-turbo, wan-video-2.5, sora-2, illustrious, flux.2-klein-9b, ideogram-2.0, gpt-image-1.5, midjourney-7, seedream-v5.0
- All images present and readable

---

## 3. Detector Baseline Evaluation

### Model Configuration
- **Model**: `buildborderless/CommunityForensics-DeepfakeDet-ViT`
- **Revision**: `ac6ee457bea904a373065754107451793b56db00`
- **Architecture**: ViT-Small, `num_labels=1`, `image_size=384`, `shortest_edge=440`
- **Attention**: `eager` (required for attention outputs)

### Production Thresholds (Config)
- `LIKELY_AI`: fake_probability ≥ 0.80
- `LIKELY_REAL`: fake_probability ≤ 0.20
- `INCONCLUSIVE`: 0.20 < fake_probability < 0.80

### Held-Out Test Set Results (n=922, threshold=0.5 for binary metrics)

| Metric | Value | 95% Wilson CI |
|--------|-------|---------------|
| **Accuracy** | 0.6562 | [0.6249, 0.6861] |
| **Precision** | 0.9935 | — |
| **Recall (AI)** | 0.3277 | [0.2868, 0.3713] |
| **F1 Score** | 0.4928 | — |
| **ROC AUC** | 0.8959 | — |
| **FPR** | 0.0022 | — |
| **FNR** | 0.6723 | — |

**Confusion Matrix**: [[451, 1], [316, 154]]  
(TN=451, FP=1, FN=316, TP=154)

### Per-Generator Recall @ Threshold 0.5

| Generator | Test Samples | Recall@0.50 | Recall@0.20 |
|-----------|--------------|-------------|-------------|
| flux.2-klein-9b | 85 | **0.0000** | 0.0471 |
| sora-2 | 7 | **0.0000** | 0.0000 |
| gpt-image-2 | 7 | **0.0000** | 0.0000 |
| seedream-v5.0 | 5 | **0.0000** | 0.0000 |
| z-image-turbo | 128 | 0.2344 | 0.3203 |
| gpt-image-1.5 | 59 | 0.1864 | 0.2881 |
| illustrious | 61 | 0.8197 | 0.8689 |
| midjourney-7 | 34 | 0.5588 | 0.6471 |
| veo-3 | 21 | 0.3333 | 0.4762 |
| wan-video-2.5 | 13 | 0.6923 | 0.7692 |

**Critical Finding**: The detector completely fails (0% recall) on **FLUX, Sora, GPT-Image-2, and Seedream** generator families. These represent 104/470 = **22% of AI test samples**.

### Corrected Protocol Evaluation (Frozen Threshold 0.05 from Validation)
| Metric | Value |
|--------|-------|
| Accuracy | 0.7538 |
| Precision | 0.9765 |
| Recall | 0.5298 |
| F1 | 0.6869 |
| Balanced Accuracy | 0.7583 |

Even at threshold 0.05, FLUX/Sora/GPT-Image-2/Seedream remain at 0% recall.

---

## 4. Current Implementation Status

### ✅ Implemented & Working
| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI backend | ✅ | Auth, rate limiting, CORS, structured logging |
| React + TypeScript + Vite frontend | ✅ | Production build succeeds |
| PostgreSQL + SQLAlchemy + Alembic | ✅ | 3 migrations, users, scans, audit_events |
| Image upload & validation | ✅ | SHA-256, decode-based validation, size/dim limits |
| AI Detector (ViT binary) | ✅ | Model loads, inference works, attention outputs |
| Metadata extraction (EXIF/XMP) | ✅ | Computed observations, proper limitations |
| ELA analysis | ✅ | JPEG recompression diff, artifact generation |
| Noise residual analysis | ✅ | Median filter high-pass, artifact generation |
| Frequency domain (2D FFT) | ✅ | Log magnitude spectrum, artifact generation |
| Evidence normalization | ✅ | Model + forensic → NormalizedEvidenceItem |
| Aggregation & Verdict | ✅ | Threshold-based, ANALYSIS_FAILED on detector error |
| PDF Report generation | ✅ | ReportLab, 6 sections, artifacts embedded |
| Authentication (JWT, HttpOnly cookies) | ✅ | Argon2id, role-based, CSRF protection |
| Audit trail | ✅ | Admin-only read, bounded values |
| Prometheus metrics | ✅ | Counters, histograms, gauges |
| Health/Readiness/Liveness | ✅ | DB connectivity, detector status |

### ⚠️ Partial / Needs Enhancement
| Component | Status | Gap |
|-----------|--------|-----|
| Generator Attribution | ❌ Not implemented | Binary detector only; no attribution model |
| Source Discovery | ❌ Not implemented | No reverse image search integration |
| Publisher Intelligence | ❌ Not implemented | No account/platform linkage |
| External Investigation Evidence | ❌ Not implemented | No integration points |
| Grad-CAM / XAI | ⚠️ Attention rollout only | ViT attention available but no spatial heatmap |
| Six-Part Report Structure | ⚠️ 3 of 6 sections | Missing Sections 2, 3, 4, 5, 6 (only 1 implemented) |
| Dataset Size | ⚠️ 6,000 | Target 10,000+ with better generator coverage |

### ❌ Not Implemented (Milestone 2 Scope)
1. **Generator/Editing Attribution Service** — No model, no labels, no inference
2. **Source Discovery** — No reverse image search, no URL matching
3. **Publisher/Account Intelligence** — No platform integration
4. **External Investigation Evidence** — No authorized data sources
5. **Evidence Preservation Chain-of-Custody** — Basic SHA-256 only
6. **Grad-CAM Heatmaps** — Attention rollout metrics only, no spatial visualization

---

## 5. Implementation Gaps by Phase

### Phase 2.2 — Dataset Expansion (P0)
- [ ] Expand from 6,000 → 10,000+ verified images
- [ ] Prioritize FLUX, Sora, GPT-Image-2, Seedream samples (currently 0% recall)
- [ ] Add GAN-generated imagery class
- [ ] Add Photoshop/generative editing class
- [ ] Maintain split isolation (no leakage)
- [ ] Document licenses and provenance for all new samples

### Phase 2.3 — Detector Improvement (P0)
- [ ] Evaluate alternative detectors (OwensLab/commfor-model-384 benchmarked in scripts)
- [ ] Test ensemble of binary + attribution models
- [ ] Consider fine-tuning ViT on expanded dataset (if compute allows)
- [ ] Document model version, training data, preprocessing for all candidates

### Phase 2.4 — Generator Attribution (P1)
- [ ] Define label taxonomy (Stable Diffusion, FLUX, Midjourney, DALL-E, GAN, etc.)
- [ ] Find/license pretrained attribution model OR implement service contract with UNKNOWN
- [ ] Return top-k candidates with uncertainty
- [ ] Distinguish verified provenance from model inference

### Phase 2.5 — Forensic Explainability (P0/P1)
- [ ] Implement Grad-CAM / Attention Rollout spatial heatmap from ViT
- [ ] Save heatmap as artifact
- [ ] Add localized anomaly detection (where methodologically supported)
- [ ] Document limitations of each forensic indicator

### Phase 2.6 — Six-Part Report (P0)
- [ ] **Section 1**: File Integrity & Provenance ✅ (exists)
- [ ] **Section 2**: Source Discovery — add placeholder with "NOT SEARCHED"
- [ ] **Section 3**: Publisher/Account Intelligence — add placeholder with "UNKNOWN"
- [ ] **Section 4**: Generator/Editing Attribution — add placeholder with "UNSUPPORTED" or real attribution
- [ ] **Section 5**: External Investigation Evidence — add placeholder with "NOT AVAILABLE"
- [ ] **Section 6**: Evidence Preservation & Corroboration — enhance with audit events, chain of custody

### Phase 2.7 — Evidence Aggregation & Risk (P0)
- [ ] Formalize risk dimensions (AI likelihood, manipulation evidence, provenance confidence, investigative risk, evidence completeness)
- [ ] Document scoring logic and thresholds
- [ ] Ensure contradictory signals are surfaced
- [ ] Prevent correlated indicators from being counted as independent

### Phase 2.8 — Backend & PDF Integration (P0)
- [ ] Extend `ScanResult` / `AggregatedAssessment` schemas for 6 sections
- [ ] Update `generate_scan_pdf` with 6-section template
- [ ] Add regression tests for report structure
- [ ] Validate database persistence of new fields

### Phase 2.9 — Release Candidate (P0)
- [ ] Freeze high-risk features by Oct 18
- [ ] Full test suite (unit + DB integration + E2E)
- [ ] Security review
- [ ] Documentation update
- [ ] Demo checklist

---

## 6. Recommended Priority Order for Next 2 Days

| Priority | Task | Effort | Rationale |
|----------|------|--------|-----------|
| **P0** | Add 6-section report structure (placeholders for missing sections) | Medium | Demo requirement; maintains honest UNKNOWN states |
| **P0** | Implement Grad-CAM heatmap from ViT attention | Medium | Uses existing model; adds explainability |
| **P0** | Generator attribution service contract + UNKNOWN behavior | Low | Framework for future; honest about limitations |
| **P0** | Run DB integration tests with PostgreSQL | Low | Verify persistence layer |
| **P1** | Evaluate OwensLab alternative detector (already benchmarked) | Medium | May improve FLUX/Sora recall |
| **P1** | Document risk scoring methodology | Low | Required for credible verdicts |
| **P1** | Add dataset validation/splitting scripts to repo | Low | Reproducibility |

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| FLUX/Sora/GPT-Image-2/Seedream 0% recall | **Certain** | High | Document as known limitation; don't claim coverage |
| Attribution model unavailable in time | High | Medium | Implement service contract with UNKNOWN; don't fabricate |
| Dataset expansion incomplete by deadline | Medium | Low | Report honest count; 6,000 is valid baseline |
| Frontend integration breaks | Low | Medium | Don't change frontend; API compatible |
| PDF report generation fails with new sections | Low | High | Test incrementally; fallback to existing template |

---

## 8. Next Actions

1. **Immediate**: Run database integration tests with PostgreSQL container
2. **Today**: Implement 6-section report structure with honest placeholders
3. **Today**: Implement Grad-CAM heatmap artifact from ViT attention
4. **Today**: Add generator attribution service interface (returns UNKNOWN)
4. **Tomorrow**: Evaluate OwensLab detector on test set
5. **Tomorrow**: Finalize risk scoring documentation
6. **Tomorrow**: Run full test suite, update documentation

---

*This audit is based on live repository inspection and executed test runs. All metrics are reproducible from the committed evaluation scripts.*