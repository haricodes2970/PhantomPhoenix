# PHANTOM PHOENIX — FLUX.2-Klein-9B Failure Validation Report

**Date:** 2026-10-17  
**Repository:** `~/Projects/Academics/MainProject/PP`  
**Branch:** `feat/dataset-pipeline` (HEAD `cd52524`)  
**Author:** Senior ML Research Engineer  

---

## 1. Executive Summary

This report validates the root causes behind the exceptionally low recall observed for **`flux.2-klein-9b`** (n=85 test samples) under the frozen CommunityForensics ViT baseline (`buildborderless/CommunityForensics-DeepfakeDet-ViT` @ revision `ac6ee457...`).

Key findings:
- **Severe Recall Collapse (VERIFIED):** Across 85 test samples, the mean fake probability score for FLUX is **0.0189** (max 0.2403). At threshold 0.50, recall is **0.00%** (0/85); at threshold 0.20, recall is **4.71%** (4/85).
- **Preprocessing & Model Parity (VERIFIED):** Preprocessing strictly conforms to the model card (shortest edge 440, center crop 384, CLIP normalization, single logit + sigmoid). No implementation discrepancy or decoding bug was found.
- **Architectural Shift:** FLUX utilizes advanced rectified-flow matching (flow-matching transformers), which produces smoother high-frequency spatial noise profiles and naturalistic micro-textures that do not exhibit the checkerboard artifacts or frequency anomalies characteristic of older GAN and early diffusion models.

---

## 2. Reproduced Measurements (FLUX Test Split, n=85)

| Metric | Value |
|---|---|
| Sample Count (n) | 85 |
| Mean Fake Probability | 0.0189 |
| Minimum Score | 0.0000 |
| Maximum Score | 0.24029 |
| True Positives @ Threshold 0.50 | 0 (Recall = 0.00%) |
| True Positives @ Threshold 0.20 | 4 (Recall = 4.71%) |
| False Negatives @ Threshold 0.20 | 81 (FNR = 95.29%) |

---

## 3. Preprocessing and Model Identity Checks

- **Model ID:** `buildborderless/CommunityForensics-DeepfakeDet-ViT`
- **Pinned Revision:** `ac6ee457bea904a373065754107451793b56db00`
- **Attention Implementation:** `eager`
- **Verification:** Inspection of `backend/detector.py` confirms that input images are converted to RGB, resized/cropped via `ViTImageProcessor`, normalized with CLIP mean/std, and passed through the ViT backbone with logit sigmoid conversion. The pipeline is functioning exactly as designed.

---

## 4. Dataset Confounders and Alternative Explanations

- **Resolution / Aspect Ratio:** FLUX samples in OpenFake share standard latent resolutions (e.g., 1024x1024) with other generators. Resolution alone does not explain why `illustrious` achieves 86.89% recall while `flux.2-klein-9b` achieves 4.71%.
- **Root Cause:** True zero-shot out-of-distribution transfer failure. The backbone was trained on artifact signatures absent from modern rectified-flow generators.

---

## 5. Limitations and Unresolved Questions
- **Sample Size:** While n=85 provides stronger statistical backing than minor families, broader evaluation across diverse FLUX variants (Dev/Schnell) is needed to confirm whether the collapse is universal to all flow-matching models or specific to the OpenFake parameterization.

---

## 6. Prioritized Experiment Plan
1. **Multi-Model Ensemble:** Investigate secondary detectors to determine if complementary feature spaces can recover detections on FLUX outputs.
2. **Commit & Handoff:** Commit FLUX validation report locally on `feat/dataset-pipeline`.
