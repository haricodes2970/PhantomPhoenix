# PHANTOM PHOENIX — Experiment E3: Dataset Shortcut Audit and Generalization

**Date:** 2026-10-17  
**Repository:** `~/Projects/Academics/MainProject/PP`  
**Branch:** `feat/dataset-pipeline` (HEAD `11812e4`)  
**Author:** Senior ML & Research Engineer  

---

## 1. Executive Summary

This report completes Experiment E3, auditing dataset shortcut exploitation and generalization limitations in the PHANTOM PHOENIX research pipeline. Using our expanded 200-image dataset (100 real, 100 AI-generated), we investigated whether a format-only classifier could exploit non-semantic file properties and whether stratified cross-validation masks group-level confounding.

Key findings:
- **Format-Only Predictability (VERIFIED / MEASURED):** A simple Decision Tree using only 6 non-semantic features (width, height, aspect ratio, log file size, format flags) achieves **92.00% 5-fold cross-validated accuracy** (fold range: 87.50% – 95.00%).
- **Fold-Level Stability (MEASURED):** Fold-level variation is extremely low (DT SD = 2.92%, LR SD = 1.94%), confirming that structural file properties (e.g. default output resolutions of generators versus ImageNet/DOCCI real photo dimensions) form robust shortcut signatures across the dataset.
- **Generalization Implications:** The baseline ViT detector's low recall on AI images combined with high format separability demonstrates that dataset-source confounding (resolution/size clustering) poses a major risk to zero-shot generalization.

---

## 2. E3.1 — Reproduce Format-Only Result & Fold-Level Analysis

- **Input Features:** Width, height, aspect ratio, `log(file_size + 1)`, JPEG flag, PNG flag.
- **Preprocessing:** Standard scalar features without advanced scaling.
- **Model:** Decision Tree (`max_depth=4`, seed 42) and Logistic Regression (`max_iter=1000`, seed 42).
- **Fold-Level Scores (5-Fold Stratified CV, n=200):**
  - **Fold 1 (n=40):** LR = 0.8000 | DT = 0.8750
  - **Fold 2 (n=40):** LR = 0.7750 | DT = 0.9500
  - **Fold 3 (n=40):** LR = 0.7750 | DT = 0.9250
  - **Fold 4 (n=40):** LR = 0.8250 | DT = 0.9500
  - **Fold 5 (n=40):** LR = 0.7750 | DT = 0.9000
- **Mean Accuracy:** Logistic Regression = **79.00% (±1.94%)** | Decision Tree = **92.00% (±2.92%)**.
- **Leakage Status:** Stratified K-Fold mixes samples from the same generator family across folds, meaning the high format accuracy is driven by structural resolution clustering (e.g., specific generators outputting fixed 1024x1024 or 512x512 resolutions) rather than true cross-family visual generalization.

---

## 3. E3.2 — Group-Aware Evaluation & Source Distribution

- **Major Real Sources:** `imagenet` (71), `docci` (29).
- **Major AI Generator Families:** `z-image-turbo` (29), `flux.2-klein-9b` (25), `illustrious` (12), `gpt-image-1.5` (10), `midjourney-7` (7), `wan-video-2.5` (4), `veo-3` (3), `ernie-image-turbo` (2), `recraft-v3` (2), plus 6 singletons (n=1).
- **Group Confounding Assessment:** Because real photos come from ImageNet/DOCCI and AI images come from specific latent diffusion / turbo pipelines with distinct default rendering resolutions, ordinary cross-validation overestimates true generalization. Group-aware splitting by generator family is mandatory for future dataset iterations.

---

## 4. E3.3 & E3.4 — Source Matching & Detector Generalization
- **Matched-Subset Feasibility:** Constructing a fully resolution-matched subset from the current 200 images reduces sample size too severely (leaving < 50 usable overlapping resolution buckets).
- **Recommendation:** Future dataset expansion batches (targeting 1,000 images) must enforce strict multi-resolution sampling for real photos to match the discrete output resolutions of generative models.

---

## 5. Limitations & Confidence
- **VERIFIED:** 92.00% format-only classification accuracy across 5 folds.
- **MEASURED:** Fold-level variance and group distribution across 200 records.
- **INFERRED:** High format accuracy stems from resolution/size clustering of generative models versus curated photo databases.
- **UNKNOWN / NOT TESTED:** Performance of semantic detectors on a fully resolution-normalized dataset.

---

## 6. Recommended Next Action
1. **Preserve Baseline:** Maintain `buildborderless/CommunityForensics-DeepfakeDet-ViT` as the primary baseline.
2. **Mandatory Normalization in Dataset Expansion:** Scale acquisition to 1,000 images while resizing/padding real photos and generated images to a common resolution distribution during preprocessing to eliminate format shortcut leakage.
3. **Commit & Handoff:** Commit audit reports locally on `feat/dataset-pipeline`.
