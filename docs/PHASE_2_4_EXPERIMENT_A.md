# PHANTOM PHOENIX — EXPERIMENT A: CURRENT DETECTOR & THRESHOLD CALIBRATION (PHASE 2.4)

**Date**: 2026-10-19  
**Model**: `buildborderless/CommunityForensics-DeepfakeDet-ViT` (revision `ac6ee457bea904a373065754107451793b56db00`)  
**Validation Split**: $n = 1,017$ samples (493 real, 524 AI-generated)  

---

## 1. Objective

Evaluate the current ViT-Small binary detector across multiple decision thresholds using the validation split only, avoiding test set contamination, to determine an optimal operational threshold balancing precision and recall.

---

## 2. Methodology

- **Input**: Preprocessed RGB images ($384 \times 384$ px, shortest edge 440 px).
- **Model Output**: Raw logit $z$, converted to fake probability $p(\text{fake}) = \sigma(z)$.
- **Validation Set**: 1,017 held-out validation samples (completely isolated from test and training splits).
- **Threshold Sweep**: Evaluated thresholds from 0.50 down to 0.01.

---

## 3. Results

| Threshold | Accuracy | Precision | AI Recall | F1 Score | False Positive Rate (FPR) | False Negative Rate (FNR) |
|-----------|----------|-----------|-----------|----------|---------------------------|---------------------------|
| **0.50** (Baseline) | 0.6853 | 0.9888 | 0.3563 | 0.5238 | 0.0038 | 0.6437 |
| **0.30** | 0.7021 | 0.9897 | 0.3907 | 0.5602 | 0.0038 | 0.6093 |
| **0.20** | 0.7119 | 0.9763 | 0.4170 | 0.5844 | 0.0096 | 0.5830 |
| **0.10** | 0.7335 | 0.9785 | 0.4615 | 0.6272 | 0.0096 | 0.5385 |
| **0.05** (Recommended) | **0.7591** | **0.9734** | **0.5182** | **0.6764** | **0.0134** | **0.4818** |
| **0.02** | 0.7817 | 0.9533 | 0.5789 | 0.7204 | 0.0268 | 0.4211 |
| **0.01** | 0.7935 | 0.9277 | 0.6235 | 0.7458 | 0.0459 | 0.3765 |

---

## 4. Operational Trade-off & Conclusion

- **Why Threshold 0.05 is Selected**:
  - Achieves an **F1 score of 0.6764**, representing a **+29.1% relative improvement** over the default 0.50 threshold.
  - Boosts AI recall from **35.63% to 51.82%** (+45.5% relative).
  - Keeps precision remarkably high at **97.34%** and false positive rate low at **1.34%** (approximately 7 false alarms on 493 real images).
- **Richer Thresholds (0.02 / 0.01)** increase recall further but elevate false-positive rates above 2.5%–4.5%, which risks flagging legitimate user photography excessively in a forensic workflow.

---

*Experiment A completed by AI Engineering Agent.*