# PHANTOM PHOENIX — DETECTOR BASELINE AUDIT (PHASE 2.3.1)

**Date**: 2026-10-19  
**Model**: `buildborderless/CommunityForensics-DeepfakeDet-ViT`  
**Revision**: `ac6ee457bea904a373065754107451793b56db00`  

---

## 1. Model Architecture & Configuration

- **Architecture**: ViT-Small image classification model (`ViTForImageClassification`).
- **Number of Labels**: `num_labels = 1` (binary classification output via scalar logit).
- **Preprocessing (ViTImageProcessor)**:
  - Shortest edge: `440` px.
  - Crop size: `384 × 384` px.
  - Normalization: ImageNet mean/std.
- **Attention Implementation**: `"eager"` (explicitly enabled to materialize attention matrices for explainability and Grad-CAM generation).

---

## 2. Inference Semantics & Threshold Policy

- **Output Transformation**:
  - Raw model output is a scalar logit ($z$).
  - Fake probability is computed via sigmoid: $p(\text{fake}) = \sigma(z) = \frac{1}{1 + e^{-z}}$.
- **Ground Truth Mapping**:
  - `ai_generated` $\rightarrow$ Positive class ($y = 1$).
  - `real` $\rightarrow$ Negative class ($y = 0$).
- **Threshold Policies**:
  - Production screening thresholds:
    - `LIKELY_AI`: $p(\text{fake}) \ge 0.80$
    - `LIKELY_REAL`: $p(\text{fake}) \le 0.20$
    - `INCONCLUSIVE`: $0.20 < p(\text{fake}) < 0.80$
  - Binary evaluation threshold: $0.50$ (or validated threshold $0.05$).

---

## 3. Dataset Baseline Audit Integration

- **Manifest**: `datasets/manifests/dataset_manifest.csv`
- **Total Samples**: 7,000 unique valid images (3,500 real, 3,500 AI).
- **Splits**:
  - Train: 4,860
  - Validation: 1,017
  - Test: 1,123
- **Split Isolation**: Verified zero SHA-256 hash overlap across train, val, and test splits.

---

## 4. Evaluation Infrastructure

- **Evaluation Script**: `scripts/run_baseline_evaluation.py` (and test-split runners).
- **Metrics Computed**: Accuracy, Precision, Recall, F1-Score, Specificity, FPR, FNR, Confusion Matrix, ROC-AUC, PR-AUC, and per-generator family breakdown.

---

*Audit completed by AI/ML Engineering Agent.*