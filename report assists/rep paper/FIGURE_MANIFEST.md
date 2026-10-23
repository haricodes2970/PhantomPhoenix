# PHANTOM PHOENIX Research Paper — Figure Manifest

**Paper version:** 2  
**Generated figures directory:** `figures/generated/`  
**Source screenshots directory:** `figures/`

---

## Generated Figures (from `scripts/generate_figures.py`)

| File | Figure # | Title | Data Source | Purpose | Evidence Status |
|------|----------|-------|-------------|---------|-----------------|
| `fig1_architecture.pdf` | 1 | System Architecture | Implementation code review | Shows 4-layer architecture with data flow | ✅ Verified against `backend/main.py`, `frontend/src/App.tsx`, Docker Compose |
| `fig2_pipeline.pdf` | 2 | Scan Processing Pipeline | `backend/main.py:481-615` | Shows sequential + parallel steps | ✅ Verified against scan pipeline implementation |
| `fig3_evidence_model.pdf` | 3 | Evidence Provenance Model | `backend/aggregator.py:79-89`, `schemas.py` | Shows 5 evidence categories → verdict | ✅ Verified against schema |
| `fig4_verdict.pdf` | 4 | Verdict Decision Diagram | `backend/verdict.py`, `backend/aggregator.py` | Shows exact threshold logic + risk mapping | ✅ Verified against implementation |
| `fig5_database.pdf` | 5 | Database Schema + Auth | `backend/models.py`, `backend/auth.py`, `backend/audit.py` | Shows tables, FKs, auth boundary | ✅ Verified against SQLAlchemy models |
| `fig6_confusion_matrix.pdf` | 6 | Confusion Matrix (τ=0.05) | `experiment_corrected_eval/corrected_evaluation_summary.json` | Shows TP/TN/FP/FN with metrics | ✅ Verified: [[446,6],[221,249]] |
| `fig7_thresholds.pdf` | 7 | Threshold Operating Points | `experiment_threshold_eval/candidate_threshold_evaluation.json` | Compares τ=0.50, 0.20, 0.05 | ✅ Verified against all three artifacts |
| `fig8_roc_pr.pdf` | 8 | ROC & PR Curves | `experiment_baseline_eval/per_sample_predictions.json` | Computed from 922 per-image scores | ✅ Recomputed: AUC=0.8959, PR-AUC=0.9163 |
| `fig9_dataset.pdf` | 9 | Dataset Composition | `datasets/manifests/dataset_manifest.csv` | Split counts + test family distribution | ✅ Verified: 4188/890/922, family counts |
| `fig10_confounding.pdf` | 10 | Dataset Confounding (E2) | `docs/EXPERIMENT_E2_DECISION_REPORT.md` | LR/DT CV accuracy on non-semantic features | ✅ Verified: 0.7900±0.0200, 0.9200±0.0292 |
| `fig11_latency.pdf` | 11 | Inference Latency | `experiment_baseline_eval/evaluation_summary.json` | Histogram + box plot from summary stats | ⚠️ Simulated from mean/median/total |
| `fig12_per_family.pdf` | 12 | Per-Family Recall (τ=0.20) | `experiment_threshold_eval/candidate_threshold_evaluation.json` | Recall per generator family | ✅ Verified against `per_generator_family_at_0.20` |

---

## Source Screenshots (from live `pp13` staging)

| File | Figure # | Title | Captured | Purpose |
|------|----------|-------|----------|---------|
| `01-landing.png` | 13* | Landing Page | 2026-10-18 via Playwright | Shows phoenix mascot, amber CTA |
| `03-dashboard.png` | 10* | Investigator Dashboard | 2026-10-18 via Playwright | Authenticated dashboard |
| `04-upload.png` | 10* | Upload View | 2026-10-18 via Playwright | Drag-drop with preview |
| `05-results-overview.png` | 11* | Results Overview | 2026-10-18 via Playwright | Verdict band, evidence cards |
| `06-metadata-evidence.png` | 11* | Metadata & Evidence | 2026-10-18 via Playwright | Structured evidence detail |
| `07-forensic-artifacts.png` | 11* | Forensic Artifacts | 2026-10-18 via Playwright | ELA, noise, FFT gallery |

*Note: Figure numbers in paper auto-assigned by LaTeX; asterisk indicates screenshot figures interleaved with generated figures.

---

## Generation Commands

```bash
cd report\ assists/rep\ paper/scripts
python3 generate_figures.py
```

All generated figures use:
- Colorblind-aware palette (Okabe-Ito inspired)
- Vector PDF output for diagrams/charts
- 300 DPI for raster elements
- Consistent typography (10pt base, 8-9pt labels)
- IEEE-style captions with data source attribution

---

## Visual Verification

All generated PDF figures were inspected at 150 DPI render:
- No clipped labels or legends
- Axis labels readable at final size
- Color contrast sufficient for grayscale printing
- Consistent font sizes across figures
- Data values match source artifacts exactly