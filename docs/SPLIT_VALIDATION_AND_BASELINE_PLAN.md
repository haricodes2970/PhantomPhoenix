# PHANTOM PHOENIX — Split Validation and Baseline Evaluation Plan

**Date:** 2026-10-17  
**Repository:** `~/Projects/Academics/MainProject/PP`  
**Branch:** `feat/dataset-pipeline` (HEAD `ae04b03`)  
**Author:** Senior ML Evaluation Engineer  

---

## 1. Executive Summary

This plan validates the split assignment logic and establishes the rigorous baseline evaluation protocol for the PHANTOM PHOENIX 6,000-image research dataset (3,000 real, 3,000 AI-generated). 

Key findings:
- **Split Distribution (VERIFIED):** Stratified assignment (`scripts/assign_dataset_splits.py`, seed 42) yielded **Train: 4,188** (2,099 real, 2,089 AI), **Val: 890** (449 real, 441 AI), and **Test: 922** (452 real, 470 AI).
- **Leakage Controls (VERIFIED):** Cryptographic SHA-256 checks confirm **zero duplicate hashes** within or across splits, and manifest-to-file reconciliation confirms **zero missing or corrupt physical files**.
- **Source Independence & Limitations (INFERRED):** While exact-duplicate leakage is eliminated, generator families and source resolutions are stratified but not entirely disjoint (i.e. minor families with n < 5 may appear in training and test splits). A strict unseen-generator generalization test is bounded by minority sample counts.

---

## 2. Split Assignment Audit

| Split | Real Count | AI-Generated Count | Total Count | Proportion |
|-------|-----------:|-------------------:|------------:|-----------:|
| **Train** | 2,099 | 2,089 | 4,188 | 69.8% |
| **Validation** | 449 | 441 | 890 | 14.8% |
| **Test** | 452 | 470 | 922 | 15.4% |
| **Total** | **3,000** | **3,000** | **6,000** | **100.0%** |

- **Methodology:** Stratified random sampling grouped by `(label, generator_family)` with fixed random seed 42.
- **Reproducibility:** Fully reproducible via `PYTHONPATH=. .venv/bin/python scripts/assign_dataset_splits.py`.

---

## 3. Source Independence and Shortcut Risks

- **Generator Family Stratification:** Major families (`z-image-turbo`, `flux.2-klein-9b`, `imagenet`, `docci`) are represented proportionally across train, val, and test splits.
- **Resolution / Format Confounding:** As established in Experiment E2, structural resolution clustering (e.g. 1024x1024 default synthetic output vs variable real photo dimensions) presents shortcut features. Although stratified across splits, classifiers may learn resolution heuristics unless spatial pooling or augmentation is applied during future fine-tuning.
- **Unseen-Source Generalization Limit:** Because minor generator families (e.g. n=1 to 3) cannot be placed in test without removing them from training, a true unseen-generator test requires holding out entire major families (e.g. holding out all `flux` or all `midjourney` samples), which is recommended for subsequent generalization experiments.

---

## 4. Baseline Evaluation Protocol

1. **Model & Revision:** `buildborderless/CommunityForensics-DeepfakeDet-ViT` @ pinned revision `ac6ee457bea904a373065754107451793b56db00` (`attn_implementation="eager"`).
2. **Preprocessing:** `ViTImageProcessor` (shortest edge 440, center crop 384, CLIP normalization).
3. **Threshold:** Evaluation decision threshold = 0.50 (distinct from production 0.80 / 0.20 policy).
4. **Target Manifest:** `datasets/manifests/dataset_manifest.csv` filtered by `split == "test"` (922 samples).
5. **Metrics to Record:**
   - Accuracy & Balanced Accuracy
   - Precision (fake class) & Recall (fake class)
   - F1 Score
   - ROC-AUC & PR-AUC
   - False Positive Rate (FPR) & False Negative Rate (FNR)
   - Confusion Matrix `[[TN, FP], [FN, TP]]`
   - Per-generator family recall
   - Inference failures and excluded samples count

---

## 5. Concrete Next Steps

1. Run the baseline evaluation protocol against the 922-sample test split using a dedicated experiment harness.
2. Record metrics and confusion matrix without altering model weights or production thresholds.
3. Commit documentation locally on branch `feat/dataset-pipeline`.
