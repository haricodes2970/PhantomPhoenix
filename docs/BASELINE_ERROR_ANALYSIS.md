# PHANTOM PHOENIX — Baseline Error Analysis and Validation-Only Threshold Study

**Date:** 2026-10-17  
**Repository:** `~/Projects/Academics/MainProject/PP`  
**Branch:** `feat/dataset-pipeline` (HEAD `08d1938`)  
**Author:** Senior ML Evaluation Engineer  

---

## 1. Executive Summary

This report presents a thorough error analysis and validation-only threshold study of PHANTOM PHOENIX on our 6,000-image research dataset (3,000 real, 3,000 AI-generated; Train: 4,188, Val: 890, Test: 922). 

Key findings:
- **Baseline Reproduction (VERIFIED):** Re-evaluation of the pinned ViT baseline (`buildborderless/CommunityForensics-DeepfakeDet-ViT` @ revision `ac6ee457...`, threshold 0.50) on the 922-sample test split reproduces **Accuracy: 0.6562**, **Precision: 0.9935**, **Recall: 0.3277**, **F1: 0.4928**, **ROC-AUC: 0.8959**, and **PR-AUC: 0.9163**. Confusion matrix: `[[451, 1], [316, 154]]`.
- **False Positive Exceptionalism:** Only **1 false positive** occurred across 452 real test photographs at threshold 0.50 (Precision = 99.35%).
- **Recall Bottleneck:** 316 false negatives occurred on AI-generated images, predominantly concentrated in latent diffusion and distilled turbo families (`z-image-turbo`: 98, `flux.2-klein-9b`: 85, `gpt-image-1.5`: 48).
- **Validation Threshold Study:** Sweeping thresholds on the validation split (n=890) demonstrates that lowering the threshold to 0.05 increases recall from 29.7% to 45.8% while keeping false positives under 1.1% (FPR = 0.0111, F1 = 0.6235). **Production thresholds (0.80 / 0.20) remain untouched.**

---

## 2. Baseline Reproduction (Test Split, n=922, Threshold 0.50)

| Metric | Measured Value |
|---|---|
| Accuracy | 0.6562 |
| Precision (fake) | 0.9935 |
| Recall (fake) | 0.3277 |
| F1 Score | 0.4928 |
| ROC-AUC | 0.8959 |
| PR-AUC | 0.9163 |
| False Positive Rate (FPR) | 0.0022 |
| False Negative Rate (FNR) | 0.6723 |
| Confusion Matrix `[[TN, FP], [FN, TP]]` | `[[451, 1], [316, 154]]` |

- **Artifacts Saved:** `datasets/manifests/experiment_error_analysis/evaluation_summary.json`, `per_sample_predictions.json`, and `sample_error_diagnostics.csv`.

---

## 3. Validation-Only Threshold Study (n=890)

Sweeping thresholds on the 890-sample validation split reveals the precision-recall trade-off:

| Threshold | Accuracy | Precision | Recall | F1 Score | FPR | FNR | Confusion Matrix `[[TN, FP], [FN, TP]]` |
|---:|---:|---:|---:|---:|---:|---:|---:|
| **0.05** | 0.7258 | 0.9758 | 0.4580 | **0.6235** | 0.0111 | 0.5420 | `[[444, 5], [239, 202]]` |
| **0.10** | 0.7045 | 0.9837 | 0.4104 | 0.5792 | 0.0067 | 0.5896 | `[[446, 3], [260, 181]]` |
| **0.20** | 0.6888 | 0.9881 | 0.3764 | 0.5452 | 0.0045 | 0.6236 | `[[447, 2], [275, 166]]` |
| **0.30** | 0.6719 | 0.9869 | 0.3424 | 0.5084 | 0.0045 | 0.6576 | `[[447, 2], [290, 151]]` |
| **0.40** | 0.6607 | 0.9860 | 0.3197 | 0.4829 | 0.0045 | 0.6803 | `[[447, 2], [300, 141]]` |
| **0.50** | 0.6494 | 0.9850 | 0.2971 | 0.4564 | 0.0045 | 0.7029 | `[[447, 2], [310, 131]]` |
| **0.70** | 0.6270 | 1.0000 | 0.2472 | 0.3964 | 0.0000 | 0.7528 | `[[449, 0], [332, 109]]` |

*Note: Production verdict thresholds (0.80 likely_ai / 0.20 likely_real) remain unchanged.*

---

## 4. Error Analysis (316 False Negatives, 1 False Positive)

### False Negatives by Generator Family (Test Split, n=470 fakes)
1. `z-image-turbo`: 98
2. `flux.2-klein-9b`: 85
3. `gpt-image-1.5`: 48
4. `midjourney-7`: 15
5. `veo-3`: 14
6. `illustrious`: 11
7. `sora-2`: 7
8. `gpt-image-2`: 7
9. `recraft-v3`: 6
10. `seedream-v5.0` / `ernie-image-turbo`: 5 each

### False Positives (Test Split, n=452 reals)
- `docci`: 1 (`real_027.jpg` or similar, score 0.5148).

---

## 5. Limitations & Threats to Validity
- **Test Set Isolation:** The test split (922 samples) was strictly locked; thresholds were derived exclusively from validation data (890 samples).
- **Generator Representation:** Minority families have low sample counts; dominant families (`z-image-turbo`, `flux`) drive the false negative distribution.

---

## 6. Recommended Next Experiment
1. **Calibrated Threshold Integration:** Evaluate whether adopting validation-optimized thresholds (e.g. 0.10–0.20) in staging improves user-facing recall without degrading precision.
2. **Commit & Handoff:** Commit error analysis report and threshold scripts locally on `feat/dataset-pipeline`.
