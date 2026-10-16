# PHANTOM PHOENIX — Threshold Selection and Locked Test Evaluation Report

**Date:** 2026-10-17  
**Repository:** `~/Projects/Academics/MainProject/PP`  
**Branch:** `feat/dataset-pipeline` (HEAD `21c2e32`)  
**Author:** Senior ML Evaluation Engineer  

---

## 1. Executive Summary

This report presents the validation-only threshold selection study and its evaluation on the locked held-out test set (922 samples: 452 real, 470 AI-generated) for PHANTOM PHOENIX.

Key findings:
- **Validation-Driven Thresholding:** Using the validation split (890 samples), we evaluated operating thresholds from 0.05 to 0.95. The default 0.50 threshold was overly conservative, yielding a high false-negative rate (~70%).
- **Candidate Operating Point (Threshold 0.20):** Selected under the operating objective of prioritizing higher fake recall while strictly bounding the False Positive Rate (FPR ≤ 0.01).
- **Locked Test Evaluation (n=922):** 
  - At **Threshold 0.50 (Baseline):** Accuracy = 0.6562, Precision = 0.9935, Recall = 0.3277, F1 = 0.4928, FPR = 0.0022.
  - At **Threshold 0.20 (Candidate):** Accuracy = **0.6941**, Precision = **0.9845**, Recall = **0.4064**, F1 = **0.5753**, FPR = **0.0066** (only 3 false positives out of 452 real photos).
  - At **Threshold 0.05 (Aggressive):** Accuracy = **0.7538**, Precision = **0.9765**, Recall = **0.5298**, F1 = **0.6869**, FPR = **0.0133** (6 false positives out of 452 real photos).

---

## 2. Validation Threshold Table (n=890)

| Threshold | Accuracy | Precision (AI) | Recall (AI) | F1 Score | FPR | FNR | Confusion Matrix `[[TN, FP], [FN, TP]]` |
|---:|---:|---:|---:|---:|---:|---:|---:|
| **0.05** | 0.7258 | 0.9758 | 0.4580 | 0.6235 | 0.0111 | 0.5420 | `[[444, 5], [239, 202]]` |
| **0.20** | 0.6888 | 0.9881 | 0.3764 | 0.5452 | 0.0045 | 0.6236 | `[[447, 2], [275, 166]]` |
| **0.35** | 0.6674 | 0.9866 | 0.3333 | 0.4983 | 0.0045 | 0.6667 | `[[447, 2], [294, 147]]` |
| **0.50** | 0.6494 | 0.9850 | 0.2971 | 0.4564 | 0.0045 | 0.7029 | `[[447, 2], [310, 131]]` |
| **0.70** | 0.6270 | 1.0000 | 0.2472 | 0.3964 | 0.0000 | 0.7528 | `[[449, 0], [332, 109]]` |

---

## 3. Candidate Selection Rationale

- **Objective:** Maximize fake-class recall subject to maintaining an operational False Positive Rate below 1% (FPR ≤ 0.01) on validation data.
- **Selection:** **Threshold 0.20** achieves an optimal balance on validation data (F1 = 0.5452, FPR = 0.0045). Threshold 0.05 yields higher recall (0.4580) but pushes FPR slightly above 1% on validation (1.11%).

---

## 4. Locked Test Set Evaluation Comparison (n=922)

| Threshold | Accuracy | Precision | Recall | F1 Score | ROC-AUC | PR-AUC | FPR | FNR | Confusion Matrix |
|---|---|---|---|---|---|---|---|---|---|
| **0.50 (Baseline)** | 0.6562 | 0.9935 | 0.3277 | 0.4928 | 0.8959 | 0.9163 | 0.0022 | 0.6723 | `[[451, 1], [316, 154]]` |
| **0.20 (Candidate)** | **0.6941** | **0.9845** | **0.4064** | **0.5753** | **0.8959** | **0.9163** | **0.0066** | **0.5936** | `[[449, 3], [279, 191]]` |
| **0.05 (Aggressive)** | **0.7538** | **0.9765** | **0.5298** | **0.6869** | **0.8959** | **0.9163** | **0.0133** | **0.4702** | `[[446, 6], [221, 249]]` |

- **Finding:** Applying Threshold 0.20 to the locked test set successfully lifts AI-image recall from **32.77% to 40.64%** while keeping false positives at a negligible level (**3 false positives out of 452 real photos**, FPR = 0.0066). Accuracy increases from 65.62% to 69.41%.

---

## 5. Per-Generator Family Breakdown at Threshold 0.20 (Test Set)

| Generator Family | Total Samples (n) | True Positives (TP) | False Negatives (FN) | False Positives (FP) | True Negatives (TN) |
|---|---:|---:|---:|---:|---:|
| `imagenet` (real) | 304 | — | — | 2 | 302 |
| `docci` (real) | 148 | — | — | 1 | 147 |
| `z-image-turbo` | 128 | 41 | 87 | 0 | 0 |
| `flux.2-klein-9b` | 85 | 4 | 81 | 0 | 0 |
| `illustrious` | 61 | 53 | 8 | 0 | 0 |
| `gpt-image-1.5` | 59 | 17 | 42 | 0 | 0 |
| `midjourney-7` | 34 | 22 | 12 | 0 | 0 |
| `veo-3` | 21 | 10 | 11 | 0 | 0 |
| `wan-video-2.5` | 13 | 10 | 3 | 0 | 0 |

---

## 6. Limitations and Conclusions
- **Threshold Selection Separability:** Validation data was strictly used for threshold selection; the test set was evaluated exactly once.
- **Model Behavior:** Production backend defaults and detector weights remain unmodified. The evaluation demonstrates that operating threshold calibration significantly improves recall without compromising real-image integrity.

---
**Report complete.**
