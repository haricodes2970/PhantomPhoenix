# PHANTOM PHOENIX — Alternative Detector Benchmark Report

**Date:** 2026-10-17  
**Repository:** `~/Projects/Academics/MainProject/PP`  
**Branch:** `feat/dataset-pipeline` (HEAD `e2a1fc1`)  
**Author:** Senior ML Research Engineer & Evaluation Lead  

---

## 1. Executive Summary

This report completes the benchmark evaluation of the Community Forensics model (`OwensLab/commfor-model-384`) against our production baseline (`buildborderless/CommunityForensics-DeepfakeDet-ViT`) on the locked 922-sample test split (452 real, 470 AI-generated).

Key findings:
- **Checkpoint Parity (VERIFIED):** Verification confirms that `buildborderless/CommunityForensics-DeepfakeDet-ViT` is the official Hugging Face `transformers`-compatible port of `OwensLab/commfor-model-384` (revision `6076002bf0d9dd37537f965ee2f06f826c333b61`, MIT License). Running inference with either entrypoint yields identical logits and scores.
- **Measured Metrics (MEASURED, n=922 test samples, threshold 0.50):**
  - **Accuracy:** `0.6562`
  - **Precision (fake):** `0.9935` (only 1 false positive across 452 real photos)
  - **Recall (fake):** `0.3277` (154 TP, 316 FN)
  - **F1 Score:** `0.4928`
  - **ROC-AUC:** `0.8959`
  - **PR-AUC:** `0.9163`
  - **Confusion Matrix:** `[[451, 1], [316, 154]]`
- **Engineering Recommendation:** **RETAIN CURRENT DETECTOR**. The current production detector is already the exact Hugging Face distribution of the target alternative checkpoint. No replacement is necessary.

---

## 2. Reproducible Benchmark Command

```bash
cd ~/Projects/Academics/MainProject/PP
PYTHONPATH=. .venv/bin/python scripts/benchmark_alternative_detector.py
```
Outputs saved to `datasets/manifests/experiment_alternative_benchmark/`.

---

## 3. Artifact Locations & Verification Results
- **Summary:** `datasets/manifests/experiment_alternative_benchmark/evaluation_summary.json`
- **Predictions:** `datasets/manifests/experiment_alternative_benchmark/per_sample_predictions.json`
- **Unit & Dataset Tests (`make test`):** **74 passed, 1 skipped**.
- **Frontend Build (`make build`):** **Successful**.
