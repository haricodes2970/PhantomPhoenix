# PHANTOM PHOENIX — Alternative Detector Benchmark & Checkpoint Audit

**Date:** 2026-10-17  
**Repository:** `~/Projects/Academics/MainProject/PP`  
**Branch:** `feat/dataset-pipeline` (HEAD `8fbf21f`)  
**Author:** Senior ML Research Engineer  

---

## 1. Executive Summary

This report documents the checkpoint audit and feasibility assessment for evaluating an alternative image detector (`OwensLab/commfor-model-384`) against our frozen baseline (`buildborderless/CommunityForensics-DeepfakeDet-ViT`) to address the FLUX.2-Klein-9B recall failure.

In accordance with strict safety rules and Task 4 ("*If the model is not already available locally, stop and report the proposed download, size, license, and resource requirements before downloading*"), **we have paused execution prior to downloading new weights** and submitted this audit for review.

---

## 2. Baseline Model Audit

- **Baseline Model ID:** `buildborderless/CommunityForensics-DeepfakeDet-ViT`
- **Pinned Revision:** `ac6ee457bea904a373065754107451793b56db00`
- **Architecture:** ViT-Small (`num_attention_heads=6`, `image_size=384`, `num_labels=1`).
- **Performance (Held-Out Test Split, n=922):** Accuracy = 65.62%, Precision = 0.9935, Recall = 0.3277, ROC-AUC = 0.8959.

---

## 3. Candidate Alternative Audit (`OwensLab/commfor-model-384`)

- **Candidate Model ID:** `OwensLab/commfor-model-384`
- **Proposed Download Size:** ~83 MB (`model.safetensors` + `config.json`).
- **Local Cache Status:** `config.json` is present locally, but model weights (`model.safetensors`) are **not** present in the Hugging Face cache.
- **License & Intended Use:** Research and academic evaluation under non-commercial terms.
- **Resource Requirements:** ~83 MB storage, ~300 MB VRAM runtime footprint (compatible with NVIDIA RTX 3050 4GB VRAM).

---

## 4. Halting Gate & Recommendation

Per Task 4 and safety rules, we **stop here** and report the proposed download before executing any weight acquisition or comparative evaluation.

### Next Steps (Pending Approval):
1. Authorize download of `OwensLab/commfor-model-384` weights.
2. Run comparative evaluation on the 922-sample test split.
3. Compare false-negative distributions on FLUX.2-Klein-9B.
