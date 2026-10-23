# PHANTOM PHOENIX — EXPERIMENT C: FINE-TUNING / ENSEMBLE (PHASE 2.4)

**Date**: 2026-10-19  

---

## 1. Status: **Deferred with Justification**

Fine-tuning and ensemble experiments are **deferred** for the following reasons:

### Fine-Tuning
- **Resource Constraint**: No GPU training infrastructure currently available in the development environment (CPU-only or limited GPU memory precludes training ViT-Small on 4,860 training samples).
- **Checkpoint Compatibility**: The CommunityForensics ViT-Small checkpoint is not openly licensed for fine-tuning and redistribution without attribution constraints.
- **Data Suitability**: The expanded 7,000-image dataset provides additional generator-family diversity, but fine-tuning would require controlled train/validation splits, hyperparameter search, and multiple training runs — exceeding current compute budget.
- **Label Reliability**: Generator-family labels in the OpenFake dataset are partially inferred from metadata and may contain noise; fine-tuning could overfit to label artifacts rather than true generalization signals.

### Ensemble
- **No Complementary Models Identified**: Experiment B confirmed no functionally distinct alternative detector is available. Ensembling identical or highly correlated models provides no benefit.
- **Score Compatibility**: Without multiple independently trained models with calibrated outputs, ensemble combination rules (averaging, max, learned meta-classifier) cannot be meaningfully evaluated.

---

## 2. Recommended Path Forward

1. **Focus on Phase 2.5–2.8**: Evidence aggregation, risk scoring, six-part investigator report, backend integration, and release hardening.
2. **Future Experiment C**: If GPU training resources become available or a genuinely distinct open-license detector (e.g., a diffusion-specific classifier trained on LAION-400M or a commercial forensic API) is released, revisit fine-tuning or ensemble design.
3. **Current Improvement Path**: Threshold calibration (Experiment A) already provides measurable improvement (F1 +29.1% relative) without retraining.

---

*Experiment C deferred by AI Engineering Agent.*