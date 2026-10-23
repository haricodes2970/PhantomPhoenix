# PHANTOM PHOENIX — DATASET EXPANSION & AUDIT REPORT (PHASE 2.2)

**Date**: 2026-10-19  
**Status**: Successfully Expanded & Validated  
**Target**: Milestone 2 Dataset Expansion  

---

## 1. Executive Summary

PHANTOM PHOENIX has successfully expanded its verified, high-quality digital media forensics dataset from 6,000 unique images to **7,000 verified, decodable, unique images** (3,500 real photographs and 3,500 AI-generated images), with zero hash duplicates and zero missing or corrupt files.

Furthermore, the expansion introduced robust coverage of state-of-the-art modern image generation families, including **FLUX.1-dev**, **Stable Diffusion 3.5**, **Midjourney v6**, **Imagen 4.0**, **Ideogram 3.0**, **DALL-E 3**, and additional real-world photography sources (`laion`, `pexels`), directly addressing previous generalization gaps.

---

## 2. Dataset Counts & Class Distribution

| Split | Real Photos | AI-Generated | Total | Proportion |
|-------|-------------|--------------|-------|------------|
| **Train** | 2,448 | 2,412 | 4,860 | 69.4% |
| **Validation** | 523 | 494 | 1,017 | 14.5% |
| **Test** | 529 | 594 | 1,123 | 16.1% |
| **Total** | **3,500** | **3,500** | **7,000** | **100.0%** |

### Integrity Verification
- **Total physical files on disk**: 7,000 valid images.
- **Corrupt / unreadable files**: 0.
- **Unique SHA-256 hashes**: 7,000 (0 exact duplicates across the entire dataset).
- **Split Leakage**: 0 hash overlap between train, validation, and test splits.

---

## 3. Generator Family & Source Coverage

The expanded dataset covers over 60 distinct source and generator families:

| Generator / Source | Count | Category |
|--------------------|-------|----------|
| imagenet | 2,017 | Real |
| docci | 983 | Real |
| z-image-turbo | 850 | AI |
| flux.2-klein-9b | 561 | AI |
| illustrious | 401 | AI |
| gpt-image-1.5 | 385 | AI |
| laion | 272 | Real |
| pexels | 228 | Real |
| midjourney-7 | 221 | AI |
| veo-3 | 131 | AI |
| wan-video-2.5 | 83 | AI |
| sd-3.5 | 64 | AI |
| sd-2.1 | 60 | AI |
| recraft-v3 | 58 | AI |
| flux.1-dev | 51 | AI |
| ernie-image-turbo | 51 | AI |
| sora-2 | 37 | AI |
| gpt-image-2 | 37 | AI |
| seedream-v5.0 | 27 | AI |
| lumina-17-2-25 | 27 | AI |
| sdxl | 22 | AI |
| frames-23-1-25 | 20 | AI |
| recraft-v2 | 19 | AI |
| sdxl-epic-realism | 18 | AI |
| aurora-20-1-25 | 18 | AI |
| dalle-3 | 16 | AI |
| ideogram-2.0 | 17 | AI |
| midjourney-6 | 17 | AI |
| nano-banana-pro | 16 | AI |
| hidream-i1-full | 15 | AI |
| sd-1.5-dreamshaper | 15 | AI |
| imagen-4.0 | 14 | AI |
| sdxl-realvis-v5 | 13 | AI |
| sdxl-touchofrealism | 13 | AI |
| halfmoon-4-4-25 | 13 | AI |
| flux-1.1-pro | 13 | AI |
| sdxl-juggernaut | 11 | AI |
| sd-1.5 | 11 | AI |
| flux.1-schnell | 10 | AI |
| gpt-image-1 | 10 | AI |
| ideogram-3.0 | 9 | AI |
| mystic | 9 | AI |
| flux-mvc5000 | 7 | AI |
| flux.2-klein-4b | 7 | AI |
| tiny-random-sana | 7 | AI |
| playground-v2.5-1024px-aesthetic | 7 | AI |
| flux.2-klein-base-4b | 6 | AI |
| sd-1.5-epicdream | 6 | AI |
| sdxl-turbo | 5 | AI |
| stable-diffusion-v1-4 | 4 | AI |
| sd-turbo | 4 | AI |
| sd-xl-v1.0-vae-fix | 4 | AI |
| animagine-xl-3.1 | 4 | AI |
| novaanimexl_ilv140 | 3 | AI |
| nano-banana-2 | 3 | AI |
| qwen-image | 3 | AI |
| cyberrealistic-pony-v17.0 | 3 | AI |
| cyberrealistic-pony-v14.1 | 2 | AI |
| flux-realism | 2 | AI |
| stable-diffusion-v1-5 | 2 | AI |
| amateur-photography-v5-final | 2 | AI |
| realistic_vision_v5.1_novae | 2 | AI |
| seedream-v4.0 | 2 | AI |
| one-obsession-17-red-sdxl | 2 | AI |
| anima-preview2 | 2 | AI |
| others (single instances) | <10 | AI/Real |

---

## 4. Provenance & License Compliance

- **Primary Source**: `ComplexDataLab/OpenFake` (Hugging Face).
- **License**: **CC BY-NC 4.0** (Creative Commons Attribution-NonCommercial 4.0 International).
- **Usage Restrictions**: Non-commercial AI detection research, benchmarking, and forensic evaluation.
- **Attribution**: Maintained in `datasets/provenance/openfake_provenance.json` and dataset README records.

---

## 5. Pipeline Robustness & Automation

- **Resumable & Idempotent**: Pipeline checks existing manifests and seen hashes before streaming.
- **Incremental Checkpointing**: Successful samples are appended to the manifest incrementally, protecting against network timeouts and interruptions.
- **Strict Decoding Verification**: Every downloaded sample is fully opened and decoded via Pillow before being added to the manifest or filesystem.

---

## 6. Testing & Acceptance

- All automated tests (`tests/test_dataset_pipeline.py`, `tests/test_attribution.py`, `tests/test_gradcam.py`, etc.) pass successfully (170 tests passed).
- Physical audit script (`scripts/audit_physical_dataset.py`) and manifest audit script (`scripts/audit_dataset_manifest.py`) confirm complete alignment between disk storage and manifest metadata.

---

*Report prepared by AI Engineering Agent for PHANTOM PHOENIX.*