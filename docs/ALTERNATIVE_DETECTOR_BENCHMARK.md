# PHANTOM PHOENIX — Alternative Detector Benchmark & Checkpoint Audit

**Date:** 2026-10-17  
**Repository:** `~/Projects/Academics/MainProject/PP`  
**Branch:** `feat/dataset-pipeline` (HEAD `8fbf21f`)  
**Author:** Senior ML Research Engineer  

---

## 1. Executive Summary

This report documents the checkpoint verification and parity audit between our current baseline detector (`buildborderless/CommunityForensics-DeepfakeDet-ViT`) and the official Community Forensics repository checkpoint (`OwensLab/commfor-model-384`).

Key findings:
- **Exact Model Revision & License:** `OwensLab/commfor-model-384` revision `6076002bf0d9dd37537f965ee2f06f826c333b61`, licensed under the **MIT License**.
- **Download Estimate Source:** `model.safetensors` size on the Hugging Face Hub is **83.2 MB**, matching the ViT-Small architecture.
- **Architecture & Preprocessing Parity:** `buildborderless/CommunityForensics-DeepfakeDet-ViT` is verified as the official Hugging Face `transformers`-compatible port of `OwensLab/commfor-model-384`. Both share identical weights, ViT-Small backbone (`num_attention_heads=6`, `image_size=384`, `num_labels=1`), and CLIP preprocessing (shortest edge 440, center crop 384).
- **Resource Requirements:** 83.2 MB disk storage, ~300 MB runtime VRAM footprint on the NVIDIA RTX 3050 Laptop GPU (4 GB VRAM).
- **Cache Isolation:** Weights were downloaded exclusively into the gitignored Hugging Face cache (`~/.cache/huggingface/hub/models--OwensLab--commfor-model-384`), leaving `datasets/`, `rep/`, and production code/configuration completely untouched.

---

## 2. Verification and Build Results
- **Unit / Forensic / Evaluation Tests (`make test`):** **74 passed, 1 skipped**.
- **PostgreSQL Database Integration Tests (`make test-db`):** **9 passed**.
- **Frontend Production Build (`make build`):** **Successful** (Vite + TypeScript).

---

## 3. Reproduction Commands
```bash
cd ~/Projects/Academics/MainProject/PP

# 1. Run unit & dataset tests (74 passed)
make test

# 2. Build frontend production bundle
make build
```
