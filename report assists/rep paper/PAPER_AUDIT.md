# PHANTOM PHOENIX Research Paper — Claim Audit

**Date:** 2026-10-18  
**Paper version:** 2 (enhanced with mathematical formulations, generated diagrams, verified metrics)  
**Source commit:** `d711815` (branch `feat/dataset-pipeline`)

---

## Audit Methodology

Each claim in the paper was traced to one of:
- **SOURCE CODE** — verified in backend/frontend implementation
- **EVALUATION ARTIFACT** — verified in `datasets/manifests/experiment_*/`
- **INTERNAL DOCUMENT** — verified in `docs/*.md`
- **NOT VERIFIED** — explicitly noted as limitation or omitted

---

## Verified Claims (SOURCE CODE)

| Claim | Source File(s) | Verified |
|-------|----------------|----------|
| ViT-Small detector, revision `ac6ee457bea904a373065754107451793b56db00` | `backend/config.py:29-30`, `backend/detector.py:28` | ✅ |
| `attn_implementation="eager"` for attention tensors | `backend/detector.py:102` | ✅ |
| Single logit + sigmoid → fake probability | `backend/detector.py:158-159` | ✅ |
| Preprocessing: shortest edge 440, center crop 384, CLIP norm | `backend/detector.py:31-32, 110-119` | ✅ |
| Detector singleton with device fallback (CUDA→CPU) | `backend/detector.py:129-136, 240-257` | ✅ |
| Config mismatch validation at load time | `backend/detector.py:108-127` | ✅ |
| Evidence categories: 5 categories | `backend/aggregator.py:79-89` | ✅ |
| Verdict logic: thresholds, failure handling, risk mapping | `backend/verdict.py:8-80`, `backend/aggregator.py:115-221` | ✅ |
| Heuristic anomaly thresholds (ELA >15, Noise std >25) | `backend/aggregator.py:167-176` | ✅ |
| ELA: JPEG q90 recompress, diff, dynamic range scale | `backend/forensics/ela.py:24-43` | ✅ |
| Noise: grayscale, median 3×3, residual stats | `backend/forensics/noise.py:20-32` | ✅ |
| Frequency: grayscale, 2D FFT, fftshift, log-mag + 1e-5 | `backend/forensics/frequency.py:20-33` | ✅ |
| Metadata: EXIF via PIL.ExifTags, XMP from info dict | `backend/forensics/metadata.py:25-50` | ✅ |
| Attention rollout: last layer, mean heads, CLS→patches, entropy | `backend/detector.py:188-238` | ✅ |
| Explainability status "unavailable" when no tensors | `backend/detector.py:196-200, 213-219` | ✅ |
| Auth: Argon2id, JWT HS256, 30-min, HttpOnly/SameSite=Lax | `backend/auth.py` | ✅ |
| Audit: dedicated session, immediate commit, bounded strings | `backend/audit.py` | ✅ |
| Rate limit: in-memory, per-process, login 5/min/peer | `backend/rate_limit.py` | ✅ |
| Scan pipeline: validate → infer → forensic → normalize → verdict → persist | `backend/main.py:481-615` | ✅ |
| PDF generation via ReportLab platypus | `backend/report.py` | ✅ |
| Frontend: React 18, TypeScript, Vite, hash routing | `frontend/package.json`, `frontend/src/main.tsx` | ✅ |

---

## Verified Claims (EVALUATION ARTIFACTS)

| Claim | Artifact | Verified |
|-------|----------|----------|
| 6,000-image manifest (3k real, 3k AI) | `datasets/manifests/dataset_manifest.csv` | ✅ |
| Stratified splits: 4,188 / 890 / 922 | `scripts/assign_dataset_splits.py` + manifest | ✅ |
| Zero SHA-256 duplicates | `scripts/audit_physical_dataset.py` | ✅ |
| Test families: 128 z-image-turbo, 85 flux.2-klein-9b, etc. | `experiment_threshold_eval/per_sample_predictions.json` | ✅ |
| Test real sources: ImageNet 304, DOCCI 148 | `dataset_manifest.csv` (split=test) | ✅ |
| Validation threshold sweep (0.05–0.95) | `experiment_corrected_eval/corrected_evaluation_summary.json` | ✅ |
| Selected threshold: 0.05 (max BA) | Same artifact | ✅ |
| Frozen test at τ=0.05: Acc 0.7538, Prec 0.9765, Rec 0.5298, F1 0.6869 | Same artifact | ✅ |
| Confusion matrix: [[446,6],[221,249]] | Same artifact | ✅ |
| ROC-AUC 0.8959, PR-AUC 0.9163 | `experiment_baseline_eval/evaluation_summary.json` | ✅ |
| Threshold 0.50: Acc 0.6562, Rec 0.3277 | Same artifact | ✅ |
| Threshold 0.20: Acc 0.6941, Rec 0.4064 | `experiment_threshold_eval/candidate_threshold_evaluation.json` | ✅ |
| Per-family recall at τ=0.20 | Same artifact | ✅ |
| CPU latency: mean 39.7ms, median 27.5ms (922 images) | `experiment_baseline_eval/evaluation_summary.json:total_duration_seconds` | ✅ |
| Format-only classifier: LR 0.7900±0.0200, DT 0.9200±0.0292 | `docs/EXPERIMENT_E2_DECISION_REPORT.md` | ✅ |

---

## Claims Explicitly Limited / Not Verified

| Claim | Status | Paper Treatment |
|-------|--------|-----------------|
| Calibrated probabilities | NOT calibrated | Explicitly stated as limitation in abstract, Sec 5.1, Sec 7 |
| Unseen-generator generalization | NOT evaluated (minor families overlap) | Sec 7.1, Sec 10 |
| Evidence fusion improves accuracy | NO ablation study | Sec 7.1, Sec 10 |
| Attention rollout localizes generator artifacts | NOT proven | Sec 5.10, Sec 7.2 |
| ELA/Noise/FFT prove authenticity/forgery | THEY DO NOT | Explicit limitations in each analyzer description |
| Legal evidentiary certification | OUT OF SCOPE | Sec 3.2 |
| Distributed rate limiting | NOT implemented (single worker) | Sec 4.5, Sec 10 |
| Video/audio/multimodal | OUT OF SCOPE | Sec 3.2 |

---

## Reference Audit

| Ref | Type | Verified |
|-----|------|----------|
| [1] Park & Owens, CVPR 2025 | Peer-reviewed | ✅ DOI 10.1109/CVPR52734.2025.00772 |
| [2] Livernoche et al., arXiv 2509.09495 | Preprint (ICLR 2026 sub) | ✅ arXiv verified |
| [3] Wang et al., CVPR 2020 | Peer-reviewed | ✅ |
| [4] Zhang et al., CVPR 2019 | Peer-reviewed | ✅ |
| [5] Zhu et al., arXiv 2306.04153 | Preprint | ✅ |
| [6] Wang et al., arXiv 2210.14896 | Preprint | ✅ |
| [7] Krawetz 2007 | Workshop (Springer) | ✅ |
| [8] Li et al., TIFS 2013 | Peer-reviewed | ✅ |
| [9] Qian et al., ECCV 2020 | Peer-reviewed | ✅ |
| [10] Cozzolino & Verdoliva, TIFS 2019 | Peer-reviewed | ✅ |
| [11] Guillaro et al., TIFS 2023 | Peer-reviewed | ✅ |
| [12] Chefer et al., CVPR 2021 | Peer-reviewed | ✅ |
| [13] E2 Decision Report | Internal | ✅ Marked as internal |
| [14] Asset Manifest | Internal | ✅ Marked as internal |

---

## Mathematical Formulation Audit

| Equation | Implemented? | Source |
|----------|--------------|--------|
| (1) Sigmoid score | ✅ | `detector.py:159` |
| (2) Verdict piecewise | ✅ | `verdict.py:23-80` |
| (3) Risk with heuristic anomalies | ✅ | `aggregator.py:162-195` |
| (4) ELA difference + scaling | ✅ | `ela.py:33-43` |
| (5) 2D FFT + log-magnitude | ✅ | `frequency.py:24-28` |
| (6) Noise residual (median filter) | ✅ | `noise.py:24-27` |
| (7-13) Classification metrics | ✅ | Standard definitions |
| (14) Balanced accuracy + threshold selection | ✅ | `run_corrected_protocol_evaluation.py:121-129` |
| (15) Accuracy CI (normal approx) | ✅ | `evaluation_summary.json:accuracy_ci_95` |
| (16) Evidence tuple | ✅ | `schemas.py:84-112` |
| (17-23) Attention rollout metrics | ✅ | `detector.py:188-238` |

---

## Summary

- **All core implementation claims** verified against source code
- **All evaluation metrics** verified against frozen test artifacts
- **All limitations** explicitly documented in paper
- **No fabricated metrics, curves, or ablation results**
- **Internal reports** cited as internal, not peer-reviewed
- **Dataset confounding** honestly reported with measured numbers