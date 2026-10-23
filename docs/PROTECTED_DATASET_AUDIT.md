# Protected Dataset Integrity and Leakage Audit

**Status:** PASSED — protection snapshot created
**Tool version:** `1.0.0`  
**Created:** `2026-10-20T15:55:59.956303+00:00`  
**Source manifest:** `datasets/manifests/dataset_manifest.csv`  
**Source manifest SHA-256:** `1967510a39111cfddaf448fc6b6f1cf226da06f1879ff41e64757c8e3545ad51`

## Inventory
- Manifest rows: **10000**
- Assigned rows: **6000**
- Unassigned rows: **4000** (untouched)
- Labels: `{'ai_generated': 5000, 'real': 5000}`
- Splits: `{'test': 922, 'train': 4188, 'unassigned': 4000, 'val': 890}`
- Exact-hash uniqueness: `10000` unique hashes

## Protection artifact
- Canonical digest: `45587eb38caa8d7d753bcff234316dd989c75e67eab2776b85be2c6520a0e7d4`
- Snapshot path: `datasets/provenance/protected_dataset_snapshot.csv` if created; otherwise **not created**
- Snapshot includes assigned rows only; no rows were assigned by this audit.
- The snapshot is integrity-checkable, not cryptographically immutable.

## Confounding observations
- `original_dataset` and `original_revision` are dataset-provided metadata, not independent provenance verification.
- Generator/source distribution: `{'imagenet': 2017, 'laion': 1056, 'docci': 983, 'pexels': 944, 'z-image-turbo': 850, 'flux.2-klein-9b': 561, 'illustrious': 401, 'gpt-image-1.5': 385, 'sd-3.5': 265, 'sd-2.1': 233, 'midjourney-7': 221, 'flux.1-dev': 182, 'veo-3': 131, 'midjourney-6': 94, 'sdxl-epic-realism': 89, 'wan-video-2.5': 83, 'sdxl': 74, 'sd-1.5-dreamshaper': 65, 'sdxl-touchofrealism': 61, 'gpt-image-1': 60, 'recraft-v3': 58, 'flux-1.1-pro': 55, 'flux.1-schnell': 53, 'ernie-image-turbo': 51, 'sdxl-juggernaut': 51, 'dalle-3': 51, 'sdxl-realvis-v5': 49, 'sd-1.5': 44, 'hidream-i1-full': 44, 'ideogram-3.0': 43, 'sora-2': 37, 'gpt-image-2': 37, 'sd-1.5-epicdream': 33, 'imagen-4.0': 31, 'ernie-image': 28, 'flux.2-dev': 28, 'seedream-v5.0': 27, 'lumina-17-2-25': 27, 'flux-mvc5000': 27, 'mystic': 23, 'stable-diffusion-v1-4': 22, 'frames-23-1-25': 20, 'flux.2-klein-4b': 20, 'recraft-v2': 19, 'tiny-random-sana': 19, 'aurora-20-1-25': 18, 'flux.2-klein-base-4b': 18, 'sd-xl-v1.0-vae-fix': 18, 'ideogram-2.0': 17, 'stable-diffusion-v1-5': 17, 'sd-turbo': 17, 'nano-banana-pro': 16, 'sdxl-turbo': 15, 'playground-v2.5-1024px-aesthetic': 14, 'halfmoon-4-4-25': 13, 'qwen-image': 13, 'grok-2-image-1212': 11, 'realistic_vision_v5.1_novae': 10, 'chroma': 9, 'animagine-xl-3.1': 8, 'studio-ghibli-wan2.1-t2v-14b-v1.0': 8, 'imagen-3.0-002': 8, 'animagine-xl-4.0': 7, 'cyberrealistic-pony-v14.1': 6, 'novaanimexl_ilv140': 6, 'anima-preview': 6, 'seedream-v4.0': 6, 'cyberrealistic-pony-v17.0': 6, 'flux-amateursnapshotphotos': 5, 'kolors-v1.0': 5, 'one-obsession-17-red-sdxl': 5, 'stable-diffusion-xl-base-1.0': 5, 'flux-realism': 4, 'openflux.1': 4, 'nano-banana-2': 4, 'grok-imagine': 4, 'animagine-xl-3.0': 4, 'cyberrealistic-pony-v16.0': 4, 'cyberrealistic-pony-v15.0': 4, 'amateur-photography-v5-final': 3, 'cyberrealistic-xl-v9.0': 3, 'look-back-wan2.1-t2v-14b-v1.0': 3, 'realvisxl_v4.0': 3, 'pony': 3, 'amateur-photography-v6': 3, 'anima-preview2': 2, 'wan-video-2.2': 2, 'twbabeflux-v1': 2, 'cyberrealistic-xl-v10.0': 1, 'cyberrealistic-pony-v14.0': 1, 'ltxv-2.3': 1, 'wan-video-2.1': 1, 'sdxl-1.0': 1, 'noobai': 1, 'hunyuan-video': 1, 'seedream-v4.5': 1, 'amateur-photography-v2.0': 1}`
- Format distribution: `{'JPEG': 7842, 'PNG': 2158}`
- Label by format: `{'ai_generated': {'JPEG': 2850, 'PNG': 2150}, 'real': {'JPEG': 4992, 'PNG': 8}}`
- Split by format: `{'test': {'JPEG': 778, 'PNG': 144}, 'train': {'JPEG': 3580, 'PNG': 608}, 'unassigned': {'JPEG': 2721, 'PNG': 1279}, 'val': {'PNG': 127, 'JPEG': 763}}`
- Resolution buckets were computed from local files; distributions are observations, not causal explanations.

## Duplicate and leakage findings
- Exact duplicate IDs/hashes and assigned cross-split exact-hash conflicts are fatal protection errors if present.
- Near-duplicate detection was **not executed**; no approved existing perceptual-hash dependency was used.
- Near-duplicate review remains required before assigning unassigned rows.

## Diagnostics
- Assigned-row protection errors: **0**
- Full diagnostic row errors: **0**

## Proposed future strategy (not assignment)
1. Freeze the original assigned rows and test hashes as the historical baseline.
2. Cluster exact and near duplicates across all rows before assigning anything new.
3. Keep duplicate clusters within one future split.
4. Review ambiguous labels and provenance before eligibility.
5. Use separate source-held-out and generator-family-held-out evaluations.
6. Select thresholds on validation only, then run one frozen test evaluation.
7. Require fixed seeds and versioned manifests for any future assignment.

## Research readiness
- Google-, OpenAI-, and Midjourney-associated families are dataset-provided labels where present; independent provenance is unknown.
- Future collection requires source URL/repository, exact family/version, license, transformation history, and label evidence.

## Limitations and approval decisions
- No actual split assignments were generated.
- No near-duplicate claims are made.
- Source-held-out and generator-held-out partitions require project-lead approval after grouping review.
