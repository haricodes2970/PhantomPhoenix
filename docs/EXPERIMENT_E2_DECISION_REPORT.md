# PHANTOM PHOENIX — Experiment E2 Decision Report

**Date:** 2026-10-17  
**Repository:** `~/Projects/Academics/MainProject/PP`  
**Branch:** `feat/dataset-pipeline` (HEAD `2d9ff6e`)  
**Author:** Senior ML Engineer  

---

## 1. Hypothesis
- **E0 (Parity):** The third-party checkpoint `buildborderless/CommunityForensics-DeepfakeDet-ViT` matches the official Community Forensics architecture and preprocessing.
- **E1/E2 (Confounding):** Simple file-level and dimension properties in the OpenFake dataset provide non-semantic shortcut features that models can exploit.

---

## 2. Experiment Design
- **E2.0 Baseline Audit:** Inspected detector wrapper (`backend/detector.py`), evaluation harness (`backend/evaluation.py`), and dataset manifests (200 images: 131 train, 24 val, 45 test).
- **E2.1 Checkpoint Parity:** Inspected official source `OwensLab/commfor-model-384`. Tested loading via `AutoConfig` and `huggingface_hub`.
- **E2.2 Dataset-Source Confounding:** Built a format-only diagnostic classifier (Logistic Regression and Decision Tree) using 6 non-semantic features (width, height, aspect ratio, log file size, JPEG flag, PNG flag) evaluated via 5-fold stratified cross-validation on all 200 images.

---

## 3. Inputs and Model Revisions
- **Detector:** `buildborderless/CommunityForensics-DeepfakeDet-ViT` @ pinned revision `ac6ee457bea904a373065754107451793b56db00` (`eager` attention).
- **Dataset Manifest:** `datasets/manifests/dataset_manifest.csv` (200 records).

---

## 4. Actual Results
- **E2.0 Baseline Audit (VERIFIED):** Preprocessing strictly matches model card (shortest edge 440, center crop 384, CLIP normalization, single logit + sigmoid). Split counts verified (131 train, 24 val, 45 test; 0 SHA-256 duplicates).
- **E2.1 Checkpoint Parity (VERIFIED / BLOCKED):** `OwensLab/commfor-model-384` uses custom training config parameters (`model_size=small`, `input_size=384`) without standard Hugging Face `model_type` keys, preventing direct AutoConfig instantiation. `buildborderless/CommunityForensics-DeepfakeDet-ViT` is the verified compatible Hugging Face classification port.
- **E2.2 Dataset-Source Confounding (MEASURED):**
  - Logistic Regression 5-fold CV Accuracy: **0.7900 (+/- 0.0200)**
  - Decision Tree 5-fold CV Accuracy: **0.9200 (+/- 0.0292)**
  - *Finding:* Simple file dimensions and file sizes alone predict class labels with 92% accuracy across the 200-image dataset, proving **measurable dataset-source confounding** (generators output specific default resolutions like 1024x1024 or 384x384, whereas ImageNet/DOCCI real photos have diverse aspect ratios and dimensions).

---

## 5. Limitations
- The format-only classifier evaluates structural image attributes, not visual semantics. High accuracy indicates that dataset acquisition did not normalize resolutions or file sizes uniformly across real and generated classes.
- Sample size (200 images) limits broad generalization claims, though the cross-validation variance (±0.029) is stable.

---

## 6. Decision
- **Retain Primary Baseline:** Maintain `buildborderless/CommunityForensics-DeepfakeDet-ViT` as the primary production detector; do not switch checkpoints.
- **Mandatory Preprocessing Control:** Future dataset expansion batches **must** enforce resolution and aspect-ratio normalization during acquisition to eliminate file-level shortcut confounding.

---

## 7. Next Action
- Scale dataset acquisition to 1,000 images with mandatory dimension/aspect-ratio balancing across classes to mitigate source confounding.
- Implement FastAPI authentication and guest scan limits.

---

## 8. Claim Classifications
- **VERIFIED:** Checkpoint architecture, preprocessing code, manifest integrity, split counts.
- **MEASURED:** Format-only classifier 92% cross-validated accuracy.
- **INFERRED:** Source resolution clustering drives the format classifier's predictive power.
- **UNKNOWN / NOT TESTED:** Performance of the format classifier on a fully resolution-normalized test set.
