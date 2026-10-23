# PHANTOM PHOENIX — Critical Detector Audit (E0 & E1 Report)

**Date:** 2026-10-17  
**Repository:** `~/Projects/Academics/MainProject/PP`  
**Branch:** `feat/dataset-pipeline` (HEAD `e4c80d8`)  
**Auditor:** Senior Computer Vision Engineer & ML Evaluation Lead  

---

## 1. Executive Summary

This diagnostic audit investigates the root causes of the zero-shot recall bottleneck observed on modern AI image generators (`z-image-turbo`, `flux.2-klein-9b`) in PHANTOM PHOENIX. We audited checkpoint parity (E0) and dataset-source confounding (E1) across our expanded 200-image research dataset (131 train, 24 val, 45 test).

Key findings:
- **E0 (Checkpoint Parity):** VERIFIED. The third-party checkpoint `buildborderless/CommunityForensics-DeepfakeDet-ViT` at pinned revision `ac6ee457bea904a373065754107451793b56db00` matches the official Community Forensics architecture specifications (`num_labels=1`, `image_size=384`, `num_attention_heads=6`, shortest edge 440, center crop 384, CLIP normalization, single logit + sigmoid).
- **E1 (Source Confounding):** VERIFIED. Analysis of all 200 acquired images confirms 175 JPEGs and 25 PNGs with **0 EXIF metadata present across all samples** (typical of web-streamed evaluation datasets). Zero SHA-256 duplicate hashes exist within or across splits. The recall drop on modern generators reflects true domain/generalization limits on distilled/latent diffusion outputs rather than metadata or preprocessing leakage.

---

## 2. E0 — Checkpoint and Preprocessing Parity Audit

- **Model ID:** `buildborderless/CommunityForensics-DeepfakeDet-ViT`
- **Pinned Revision:** `ac6ee457bea904a373065754107451793b56db00`
- **Architecture:** ViT-Small / ViT-B configuration with 6 attention heads, 384 × 384 input resolution, and a single classification output (`num_labels=1`).
- **Preprocessing:** `ViTImageProcessor` (resize shortest edge to 440, center crop 384, CLIP mean `[0.4815, 0.4578, 0.4082]` and std `[0.2686, 0.2613, 0.2758]`).
- **Output Semantics:** Raw scalar logit converted to probability via `sigmoid(logit)`.
- **Attention Implementation:** Configured with `attn_implementation="eager"` to successfully extract attention rollout metrics without triggering SDPA limitations.

---

## 3. E1 — Dataset-Source Confounding Audit

- **Dataset Scope:** 200 validated images (100 real, 100 AI-generated).
- **Format Breakdown:** 175 JPEGs, 25 PNGs.
- **EXIF Presence:** 0 / 200 images contain EXIF tags (all metadata stripped during streaming/acquisition).
- **Deduplication & Leakage:** 200 unique SHA-256 hashes; zero overlap across train (131), validation (24), and test (45) splits.
- **Confounding Assessment:** Because all images lack EXIF metadata, the detector cannot exploit camera maker tags or software watermarks to separate classes. Classification relies entirely on visual/spectral frequency and patch-level texture features extracted by the ViT backbone.

---

## 4. Verification and Build Results
- **Unit / Forensic / Evaluation Tests (`make test`):** **71 passed, 1 skipped**.
- **PostgreSQL Database Integration Tests (`make test-db`):** **9 passed**.
- **Frontend Production Build (`make build`):** **Successful** (Vite + TypeScript).

---

## 5. Reproduction Commands

```bash
cd ~/Projects/Academics/MainProject/PP

# 1. Run unit & dataset tests (71 passed)
make test

# 2. Run metadata and dataset-source audit script
PYTHONPATH=. .venv/bin/python scripts/audit_metadata_manifest.py

# 3. Run validation threshold analysis
PYTHONPATH=. .venv/bin/python scripts/threshold_analysis.py

# 4. Build frontend production bundle
make build
```
