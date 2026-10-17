# PHANTOM PHOENIX — Generator-Family Generalization and Operating-Point Validation Report

**Date:** 2026-10-17  
**Repository:** `~/Projects/Academics/MainProject/PP`  
**Branch:** `feat/dataset-pipeline` (HEAD `5eaefa0`)  
**Author:** Senior ML Evaluation Engineer  

---

## 1. Executive Summary

This report evaluates generator-family generalization and validates the candidate operating threshold (0.20) across our 6,000-image dataset (Train: 4,188, Validation: 890, Test: 922).

Key findings:
- **Operating-Point Validation (MEASURED):** Adopting **Threshold 0.20** on the locked test set (922 samples) increases overall accuracy from **65.62% to 69.41%** and AI-image recall from **32.77% to 40.64%**, while maintaining an exceptionally low False Positive Rate of **0.0066** (only 3 false positives across 452 real photographs).
- **Per-Family Discrepancies:** The baseline ViT detector exhibits extreme variance across generator families. It achieves high recall on `illustrious` (86.89%), `wan-video-2.5` (76.92%), and `midjourney-7` (64.71%), but suffers severe under-detection on `flux.2-klein-9b` (4.71% recall at t=0.20) and zero detection on `sora-2`, `gpt-image-2`, and `seedream-v5.0` in this test slice.
- **Confidence Intervals (95% Wilson Score):**
  - Baseline (0.50): Accuracy = 65.62% [62.49%, 68.61%]; AI Recall = 32.77% [28.68%, 37.13%].
  - Candidate (0.20): Accuracy = 69.41% [66.36%, 72.30%]; AI Recall = 40.64% [36.29%, 45.14%].

---

## 2. Generator Distribution Across Splits (6,000 Total Images)

| Generator / Source | Train | Validation | Test | Total |
|---|---:|---:|---:|---:|
| `imagenet` (real) | 1,411 | 302 | 304 | 2,017 |
| `docci` (real) | 688 | 147 | 148 | 983 |
| `z-image-turbo` | 595 | 127 | 128 | 850 |
| `flux.2-klein-9b` | 392 | 84 | 85 | 561 |
| `illustrious` | 280 | 60 | 61 | 401 |
| `gpt-image-1.5` | 269 | 57 | 59 | 385 |
| `midjourney-7` | 154 | 33 | 34 | 221 |
| `veo-3` | 91 | 19 | 21 | 131 |
| `wan-video-2.5` | 58 | 12 | 13 | 83 |
| `recraft-v3` | 40 | 8 | 10 | 58 |
| Other minor families | 159 | 34 | 34 | 227 |
| **Total** | **4,188** | **890** | **922** | **6,000** |

---

## 3. Per-Family Test Performance (n=922 Test Samples)

| Family / Source | Test Samples (n) | Recall @ 0.50 | Recall @ 0.20 | 95% Wilson CI @ 0.20 |
|---|---:|---:|---:|---:|
| `z-image-turbo` | 128 | 0.2344 | 0.3203 | [0.2457, 0.4054] |
| `flux.2-klein-9b` | 85 | 0.0000 | 0.0471 | [0.0184, 0.1148] |
| `illustrious` | 61 | 0.8197 | 0.8689 | [0.7620, 0.9320] |
| `gpt-image-1.5` | 59 | 0.1864 | 0.2881 | [0.1884, 0.4138] |
| `midjourney-7` | 34 | 0.5588 | 0.6471 | [0.4791, 0.7851] |
| `veo-3` | 21 | 0.3333 | 0.4762 | [0.2834, 0.6763] |
| `wan-video-2.5` | 13 | 0.6923 | 0.7692 | [0.4974, 0.9182] |
| `recraft-v3` | 10 | 0.4000 | 0.6000 | [0.3127, 0.8318] |
| `ernie-image-turbo` | 9 | 0.4444 | 0.5556 | [0.2666, 0.8112] |
| `sora-2` (n=7) | 7 | 0.0000 | 0.0000 | [0.0000, 0.3543] |
| `gpt-image-2` (n=7) | 7 | 0.0000 | 0.0000 | [0.0000, 0.3543] |
| `imagenet` (real) | 304 | TN=304, FP=0 | TN=302, FP=2 | — |
| `docci` (real) | 148 | TN=147, FP=1 | TN=147, FP=1 | — |

---

## 4. Limitations & Generalization Assessment

- **Unseen-Generator Evaluation:** Because OpenFake samples span diverse generators proportionally across splits, the test set is a *same-distribution held-out split*, not a true zero-shot unseen-generator test. True unseen-generator testing requires holding out entire major families (e.g. reserving all `flux` or all `midjourney` exclusively for testing).
- **Minor Family Uncertainty:** Families with n < 10 exhibit wide confidence intervals; their recall estimates are exploratory.

---

## 5. Recommendation

- **Retain Candidate Threshold 0.20 for Research:** The validation-calibrated threshold of 0.20 provides a superior operating balance (F1 0.5753 vs 0.4928) while keeping real-image false positives exceptionally low (FPR 0.0066).
- **Next Experiment:** Design a family-held-out generalization study where specific generator families are omitted from training to measure true zero-shot transfer.
