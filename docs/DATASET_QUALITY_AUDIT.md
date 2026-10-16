# PHANTOM PHOENIX — Dataset Quality Audit and Leakage-Resistant Split Plan

**Date:** 2026-10-17  
**Repository:** `~/Projects/Academics/MainProject/PP`  
**Branch:** `feat/dataset-pipeline` (HEAD `309c34b`)  
**Auditor:** Senior ML Evaluation Engineer  

---

## 1. Executive Summary

This audit establishes the quality, integrity, provenance, and split configuration of the PHANTOM PHOENIX 6,000-image research dataset (3,000 real photographs, 3,000 AI-generated images). All physical files, manifests, hashes, and split assignments were inspected without modifying production models.

Key findings:
- **Integrity & Scale (VERIFIED):** Exactly 6,000 valid, unique, decodable physical images exist on disk (3,000 real, 3,000 AI-generated). There are **0 missing files**, **0 corrupt files**, and **0 duplicate SHA-256 hashes** across the entire dataset.
- **Provenance & Licensing (VERIFIED):** Sourced from Hugging Face `ComplexDataLab/OpenFake` (`core` config, `test` split) under **CC BY-NC 4.0** (Non-commercial research use only).
- **Split Distribution (MEASURED):** Stratified 70/15/15 assignment yielded **Train: 4,188** (2,099 real, 2,089 AI), **Val: 890** (449 real, 441 AI), and **Test: 922** (452 real, 470 AI). **Zero SHA-256 overlap** exists across splits.
- **Confounders (INFERRED):** Resolution and aspect-ratio clustering (e.g. 1024x1024 for synthetic generators vs ImageNet/DOCCI dimensions for real photos) present potential shortcut features, requiring group-aware awareness during model fine-tuning.

---

## 2. Dataset Composition and Provenance

- **Total Unique Images:** 6,000 (3,000 real, 3,000 AI-generated).
- **Source Dataset:** `ComplexDataLab/OpenFake` (Hugging Face).
- **License:** CC BY-NC 4.0 (Non-commercial research use only).
- **Real Sources:** `imagenet` (2,017), `docci` (983).
- **AI Generator Families:** `z-image-turbo` (850), `flux.2-klein-9b` (561), `illustrious` (401), `gpt-image-1.5` (385), `midjourney-7` (221), `veo-3` (131), `wan-video-2.5` (83), `recraft-v3` (58), and minor generative families.
- **Formats:** 5,121 JPEG, 879 PNG.

---

## 3. Integrity and Leakage Findings

- **Manifest Reconciliation:** Master CSV at `datasets/manifests/dataset_manifest.csv` fully reconciles with disk.
- **Exact Duplicates:** 0 exact byte duplicates across all 6,000 samples.
- **Cross-Split Leakage:** 0 SHA-256 hash intersections between train, val, and test splits.

---

## 4. Confounders and Limitations

- **Resolution Clustering:** Generative models output in fixed grid resolutions (e.g. 1024x1024), whereas ImageNet/DOCCI real photographs exhibit diverse aspect ratios and dimensions.
- **Generator Imbalance:** Major generators (`z-image-turbo`, `flux`) dominate the AI split, while minor families have small sample sizes.
- **Limitation:** Binary detection performance may partially reflect resolution/compression priors rather than pure semantic forgery artifacts.

---

## 5. Recommended Split Strategy

- **Stratified Split:** 70% Train (4,188), 15% Validation (890), 15% Test (922).
- **Leakage Controls:** Cryptographic SHA-256 deduplication and stratified sampling across `(label, generator_family)` strata.
- **Test Isolation:** The test split (922 samples) remains strictly locked against model selection, threshold tuning, and calibration.

---

## 6. Baseline Evaluation Protocol

1. **Model:** `buildborderless/CommunityForensics-DeepfakeDet-ViT` @ pinned revision `ac6ee457bea904a373065754107451793b56db00` (`attn_implementation="eager"`).
2. **Threshold:** Evaluation threshold = 0.50 (distinct from production 0.80 / 0.20 policy).
3. **Metrics:** Accuracy, Precision, Recall, F1 Score, ROC-AUC, Confusion Matrix `[[TN, FP], [FN, TP]]`, and per-generator recall.

---

## 7. Concrete Next Steps

1. Run evaluation on the expanded test split (922 samples) to measure zero-shot generalization of the baseline ViT at scale.
2. Implement FastAPI authentication and guest scan limits (3 scans).
3. Keep untracked `rep/` and pilot artifacts intact.
