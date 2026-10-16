# PHANTOM PHOENIX — Dataset Integrity and Evaluation Audit

**Date:** 2026-10-17  
**Git HEAD:** `2a3a5af` (Branch `feat/dataset-pipeline`)  
**Auditor:** Senior ML Engineer & Research Code Reviewer  

---

## 1. Executive Summary

This audit verifies the integrity of the PHANTOM PHOENIX research dataset acquisition manifests, split assignment logic, evaluation harness implementation, and baseline reproducibility. All checks were performed locally without modifying production models or downloading external data. 

Key verified facts:
- **Zero duplicates or corruption:** The 50-sample dataset manifest (`datasets/manifests/dataset_manifest.csv`) contains 50 unique SHA-256 hashes, 0 missing files, and 0 corrupt files.
- **Split distribution:** A stratified 70/15/15 split yielded Train = 28 (16 real, 12 AI), Val = 4 (3 real, 1 AI), and Test = 18 (6 real, 12 AI). Zero hash overlap exists across splits.
- **Model & Preprocessing:** The baseline ViT detector (`buildborderless/CommunityForensics-DeepfakeDet-ViT`) is pinned to revision `ac6ee457bea904a373065754107451793b56db00` with `attn_implementation="eager"`.
- **Pilot Reproduction:** Re-running the 50-image pilot evaluation yields Accuracy: 0.6200, Precision: 1.0000, Recall: 0.2400, F1: 0.3871, ROC-AUC: 0.8960, Confusion Matrix: `[[25, 0], [19, 6]]`, matching previous records exactly.

---

## 2. Dataset Manifest Audit

### A. Pipeline Dataset Manifest (`datasets/manifests/dataset_manifest.csv`)
- **Total Rows:** 50
- **Class Balance:** 25 real, 25 AI-generated (`ai_generated`)
- **SHA-256 Uniqueness:** 50 unique hashes (0 duplicates)
- **File Integrity:** 50/50 files verified readable and decodable via PIL
- **Generator Families:**
  - `z-image-turbo`: 13
  - `imagenet`: 18
  - `docci`: 7
  - `flux.2-klein-9b`: 4
  - `illustrious`: 2
  - `wan-video-2.5`: 1
  - `sora-2`: 1
  - `ideogram-2.0`: 1
  - `seedream-v5.0`: 1
  - `gpt-image-1.5`: 1
  - `midjourney-7`: 1
- **Split Distribution:**
  - `train`: 28 (16 real, 12 AI)
  - `val`: 4 (3 real, 1 AI)
  - `test`: 18 (6 real, 12 AI)
  - **Cross-split leakage:** Verified 0 overlapping hashes between train, val, and test.

### B. Pilot Dataset Manifest (`datasets/openfake_pilot/eval_manifest.csv`)
- **Total Rows:** 50 (25 real, 25 fake)
- **File Integrity:** 50/50 valid files
- **Preservation:** Maintained untouched as a diagnostic baseline reference.

---

## 3. Label and Attribution Semantics

| Raw Source Label | Normalized Class | Evidence Source | Limitations |
|------------------|------------------|-----------------|-------------|
| `"real"` / `"authentic"` | `0` (`real`) | ImageNet / DOCCI photo repositories | Real-world camera and lighting diversity is limited in benchmark samples. |
| `"fake"` / `"ai"` / `"synthetic"` | `1` (`ai_generated`) | OpenFake dataset metadata (`model` field) | Generator tags reflect provider labels; version drift or misattributions may exist. |
| Style labels (e.g. anime) | `generator_family` metadata | OpenFake `model` field | Style is not an architectural generator family; treated as metadata attribute. |
| Video frames (`wan-video-2.5`, `sora-2`) | `generator_family` metadata | OpenFake `model` field | Video-derived frames exhibit temporal artifacts distinct from native still images. |

---

## 4. Evaluator Audit (`backend/evaluation.py`)

- **Pinned Revision:** Enforced via `DetectorConfig(model_revision=settings.model_revision)`.
- **Preprocessing:** Standard `ViTImageProcessor` (shortest edge 440, crop 384).
- **Threshold Policy:** Evaluation threshold defaults to 0.5 (distinct from production policy of 0.80 / 0.20).
- **Error Handling:** Files missing from disk or raising inference exceptions are appended to `exclusions` or `inference_errors` and excluded from metric denominators rather than counted as correct/incorrect predictions.

---

## 5. Reproducibility Commands

```bash
# 1. Run unit, forensic, and evaluation tests
make test

# 2. Run dataset pipeline tests
.venv/bin/python -m pytest tests/test_dataset_pipeline.py -v

# 3. Reproduce 50-image pilot evaluation
PYTHONPATH=. .venv/bin/python scripts/run_pilot_eval.py datasets/openfake_pilot/eval_manifest.csv

# 4. Evaluate baseline detector on held-out test split
PYTHONPATH=. .venv/bin/python scripts/evaluate_heldout_test.py
```

---

## 6. License and Provenance
- **Dataset Source:** `ComplexDataLab/OpenFake` (Hugging Face `core` config, `test` split).
- **License:** **CC BY-NC 4.0** (Non-commercial research use only). Prohibits commercial deployment or proprietary redistribution.
- **Provenance Record:** Stored at `datasets/provenance/openfake_provenance.json` and `datasets/openfake_pilot/provenance.json`.
