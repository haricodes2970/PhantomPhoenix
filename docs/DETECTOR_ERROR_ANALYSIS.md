# PHANTOM PHOENIX — DETECTOR ERROR & GENERALIZATION ANALYSIS (PHASE 2.3.3)

**Date**: 2026-10-19  
**Model**: `buildborderless/CommunityForensics-DeepfakeDet-ViT`  
**Test Set**: $n = 1,123$ samples (529 real, 594 AI-generated)

---

## 1. Executive Findings

Evaluating the ViT-Small detector on the expanded 7,000-image dataset test split ($n = 1,123$) reveals:
- **High Specificity / Low False Positive Rate**: FPR is **0.0019** (only 1 false positive out of 529 real photographs across ImageNet, Docci, LAION, and Pexels sources).
- **Moderate Recall**: Overall AI recall at threshold 0.5 is **37.88%** (225 true positives out of 594 AI images).
- **Generator Family Generalization Gap**:
  - High performance on older/classic GAN and SD models (e.g. `illustrious`, `sd-2.1`, `sdxl-juggernaut`, `lumina-17-2-25` achieving 70%–100% recall).
  - Continued low or zero recall on specific high-end diffusion variants and video/multimodal generators (e.g., `flux.2-klein-9b`, `flux.2-dev`, `sora-2`, `gpt-image-2`, `seedream-v5.0`).
  - Strong performance on newly introduced dataset sources like `sd-1.5`, `sd-turbo`, `kolors-v1.0`, and `grok-imagine` (100% recall on small test samples).

---

## 2. Confusion Matrix & Core Metrics (Threshold = 0.50)

| Metric | Value |
|--------|-------|
| **Accuracy** | 0.6705 |
| **Precision** | 0.9956 |
| **Recall (AI)** | 0.3788 |
| **F1 Score** | 0.5488 |
| **ROC-AUC** | 0.8965 |
| **PR-AUC** | 0.9176 |
| **True Negatives (TN)** | 528 |
| **False Positives (FP)** | 1 |
| **False Negatives (FN)** | 369 |
| **True Positives (TP)** | 225 |
| **Specificity** | 0.9981 |
| **FPR** | 0.0019 |
| **FNR** | 0.6212 |

---

## 3. Root Cause Analysis of Errors

1. **Conservative Decision Boundary (High Precision, Low Recall)**:
   - At threshold 0.5, the model strongly avoids false positives on real images (FPR 0.19%), but classifies many subtle diffusion images as real (FNR 62.12%).
2. **Modern Generator Adaptation**:
   - Newer architectures (FLUX.2, Sora, Seedream) utilize advanced noise schedules and upsampling that leave fewer artifacts in frequency and spatial domains detectable by the ViT-Small checkpoint.
3. **Threshold Sensitivity**:
   - Lowering the decision threshold (e.g., from 0.50 to 0.05 or 0.20) increases AI recall significantly while maintaining a controlled false-positive rate.

---

## 4. Recommendations for Phase 2.3.4 & 2.3.5

- **Threshold Calibration**: Evaluate validation set score distribution to select an optimal operational threshold balancing precision and recall.
- **Controlled Experiments**: Test calibrated thresholding and examine whether alternative thresholds achieve a superior F1 balance without retraining.

---

*Error analysis completed by AI Engineering Agent.*