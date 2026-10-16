# PHANTOM PHOENIX — Baseline Evaluation Report

**Date:** 2026-10-17  
**Repository:** `~/Projects/Academics/MainProject/PP`  
**Branch:** `feat/dataset-pipeline` (HEAD `4a0005b`)  
**Evaluator:** Senior ML Evaluation Engineer  

---

## 1. Executive Summary

This report establishes the first reproducible baseline evaluation of PHANTOM PHOENIX on the locked 922-sample held-out test split of our 6,000-image research dataset (3,000 real, 3,000 AI-generated). 

Key measured findings:
- **High Precision / Low Recall:** At decision threshold 0.50, the baseline ViT detector achieves an exceptional **precision of 0.9935** (only **1 false positive** across 452 real photographs). However, recall on AI-generated images is **0.3277** (154 TP, 316 FN), illustrating a persistent zero-shot recall bottleneck on modern latent diffusion and turbo generators.
- **Strong Ranking Ability:** Despite low recall at the fixed 0.50 threshold, the detector maintains a robust **ROC-AUC of 0.8959** and **PR-AUC of 0.9163**, indicating strong relative score ranking capability.
- **Integrity & Protocol:** Evaluated on the isolated test split (922 samples) with zero train/test hash overlap and zero model/threshold tuning.

---

## 2. Model Identity and Revision

- **Model ID:** `buildborderless/CommunityForensics-DeepfakeDet-ViT`
- **Pinned Revision:** `ac6ee457bea904a373065754107451793b56db00`
- **Attention Implementation:** `eager`
- **Preprocessing:** `ViTImageProcessor` (shortest edge 440, center crop 384, CLIP normalization).
- **Decision Threshold:** Evaluated at 0.50 (diagnostic screening threshold; production policy remains 0.80 / 0.20).

---

## 3. Dataset and Split Identifiers

- **Dataset:** 6,000 unique images from Hugging Face `ComplexDataLab/OpenFake` (`core` config, `test` split, CC BY-NC 4.0).
- **Test Split Manifest:** `datasets/manifests/dataset_manifest.csv` (`split == "test"`).
- **Test Sample Support:** 922 total samples (452 real, 470 AI-generated).
- **Leakage Control:** 0 SHA-256 duplicate hashes across splits.

---

## 4. Exact Evaluation Procedure and Command

```bash
cd ~/Projects/Academics/MainProject/PP
PYTHONPATH=. .venv/bin/python scripts/run_baseline_evaluation.py
```
Outputs saved under `datasets/manifests/experiment_baseline_eval/` (`evaluation_summary.json` and `per_sample_predictions.json`).

---

## 5. Measured Metrics and Confusion Matrix

- **Evaluated Samples:** 922 / 922 (0 inference errors)
- **Accuracy:** `0.6562`
- **Precision (fake):** `0.9935`
- **Recall (fake):** `0.3277`
- **F1 Score:** `0.4928`
- **ROC-AUC:** `0.8959`
- **PR-AUC:** `0.9163`
- **FPR:** `0.0022` | **FNR:** `0.6723`
- **Confusion Matrix:**
  $$\begin{pmatrix} \text{TN} = 451 & \text{FP} = 1 \\ \text{FN} = 316 & \text{TP} = 154 \end{pmatrix}$$
  *(Format: `[[TN, FP], [FN, TP]]`)*

---

## 6. Error Analysis

- **False Positives (FP = 1):** Exceptional restraint on real photographs; only 1 real image out of 452 was misclassified as AI-generated at threshold 0.50.
- **False Negatives (FN = 316):** The primary failure mode is false negatives on AI-generated images, where the detector assigns scores below 0.50 to modern generative architectures (e.g. `z-image-turbo`, `flux.2-klein-9b`). 
- **Score Ranking:** Because ROC-AUC is high (0.8959), these false negatives represent miscalibrated decision boundaries rather than absence of signal.

---

## 7. Limitations and Threats to Validity

1. **Threshold Sensitivity:** A fixed 0.50 threshold is sub-optimal for this detector's probability distribution on OpenFake data.
2. **Generator Imbalance:** Performance varies across minor generator families due to sample size differences.
3. **Hardware:** Evaluated on NVIDIA RTX 3050 Laptop GPU (4 GB VRAM) with average inference latency of ~0.02s per image.

---

## 8. Recommended Next Steps

1. **Threshold Calibration:** Utilize the validation split (890 samples) to compute a calibrated operating threshold (e.g. optimizing F1 or Youden's J statistic) without touching the locked test set.
2. **Ensemble Exploration:** Evaluate secondary lightweight candidates (e.g. CNNDetection or frequency-domain probes) on the validation split for soft voting.
3. **Commit & Handoff:** Commit baseline evaluation report and harness locally on `feat/dataset-pipeline`.
