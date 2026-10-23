# PHANTOM PHOENIX — THRESHOLD CALIBRATION & RECOMMENDATION (PHASE 2.3.4)

**Date**: 2026-10-19  
**Model**: `buildborderless/CommunityForensics-DeepfakeDet-ViT`  
**Validation Set**: $n = 1,017$ samples (493 real, 524 AI-generated)  
**Test Set**: $n = 1,123$ samples (529 real, 594 AI-generated)

---

## 1. Validation Set Threshold Sweep

| Threshold | Accuracy | Precision | Recall (AI) | F1 Score | FPR |
|-----------|----------|-----------|-------------|----------|-----|
| **0.50** | 0.6853 | 0.9888 | 0.3563 | 0.5238 | 0.0038 |
| **0.30** | 0.7021 | 0.9897 | 0.3907 | 0.5602 | 0.0038 |
| **0.20** | 0.7119 | 0.9763 | 0.4170 | 0.5844 | 0.0096 |
| **0.10** | 0.7335 | 0.9785 | 0.4615 | 0.6272 | 0.0096 |
| **0.05** | **0.7591** | **0.9734** | **0.5182** | **0.6764** | **0.0134** |
| **0.02** | 0.7817 | 0.9533 | 0.5789 | 0.7204 | 0.0268 |
| **0.01** | 0.7935 | 0.9277 | 0.6235 | 0.7458 | 0.0459 |

---

## 2. Operational Threshold Selection

### Recommended Production Threshold: **0.05** (Validated on Validation Set)

**Justification**:
- **Balanced Trade-off**: At threshold 0.05, the model achieves **F1 = 0.6764**, a **+29.1% relative improvement** over the original 0.50 threshold (0.5238).
- **Significant Recall Gain**: AI-class recall improves from **35.6%** to **51.8%** (+45.5% relative), reducing false negatives substantially.
- **High Precision Maintained**: Precision remains **97.34%**, keeping false alarms on real images minimal.
- **Controlled False Positive Rate**: FPR at **1.34%** (≈7 false positives out of 493 real images on validation) is operationally acceptable for a forensic screening tool.

### Threshold Policy for Backend Contract

| Verdict | Fake Probability Range | Risk Level |
|---------|----------------------|------------|
| `LIKELY_AI` | $\ge 0.80$ | `HIGH` |
| `LIKELY_REAL` | $\le 0.05$ | `LOW` |
| `INCONCLUSIVE` | $0.05 < p(\text{fake}) < 0.80$ | `MODERATE` |

---

## 3. Test Set Evaluation at Validated Threshold (0.05)

*To be completed via `scripts/run_corrected_protocol_evaluation.py`*

The final test set evaluation using the frozen validation-selected threshold (0.05) will be reported upon completion of the corrected protocol run.

---

*Threshold calibration completed by AI Engineering Agent.*