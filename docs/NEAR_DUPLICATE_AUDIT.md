# Near-Duplicate Audit — Dependency Review and Completed Execution

**Date:** 2026-10-20  
**Branch:** `feat/dataset-pipeline`  
**Tool:** `scripts/audit_near_duplicates.py` v1.0.0  
**Algorithm:** dependency-free 64-bit horizontal dHash  
**Threshold:** Hamming distance <= 6  
**Workers:** 8 deterministic hash workers

## Dependency review

Actual `.venv` inspection found:

- `imagehash`: unavailable
- OpenCV (`cv2`): unavailable
- scikit-image: unavailable
- Pillow: available
- NumPy: available

No packages were installed.

## Method and optimization

The audit uses Pillow-only dHash:

1. Convert image to grayscale.
2. Resize to 9x8 with Lanczos resampling.
3. Compare horizontal adjacent pixels to create a 64-bit integer hash.
4. Search prior hashes with a BK-tree using integer `bit_count()` Hamming distance.
5. Hash computation is parallelized with an ordered `ThreadPoolExecutor`; candidate insertion/search remains deterministic and serial.

Candidate records are marked `candidate_unreviewed`. Exact SHA-256 duplicates are a separate verified category. No perceptual candidate is treated as confirmed duplication or leakage.

## Profiling

A read-only 1,000-image profile showed:

- dHash image decoding/computation: approximately 16 seconds serially.
- BK-tree insertion/search: less than 0.1 seconds for the sample.
- Estimated serial full-run cost: approximately 160 seconds.

The optimized 8-worker full run completed within the allowed execution window. The dominant bottleneck was image decoding, not BK-tree search.

## Full 10,000-image result

Command:

```bash
PYTHONPATH=. .venv/bin/python scripts/audit_near_duplicates.py \
  --output-json datasets/provenance/near_duplicate_candidates_v1.json \
  --output-csv datasets/provenance/near_duplicate_candidates_v1.csv \
  --workers 8
```

Result:

- Samples processed: **10,000**
- Candidate records: **97**
- Exact SHA-256 duplicate records: **0**
- Perceptual candidate records: **97**
- Candidate status: **`candidate_unreviewed`** for all 97
- Cross-split perceptual candidate pairs: **45**
- Candidate pairs involving at least one unassigned sample: **73**
- Candidate distance range: **1–6**
- Threshold: **6**

Output files:

```text
datasets/provenance/near_duplicate_candidates_v1.json
datasets/provenance/near_duplicate_candidates_v1.csv
```

The output records include sample IDs, SHA-256 values, split values, labels, generator families, dHash distance, and cross-split status.

## Interpretation

The 45 cross-split records are **not confirmed leakage**. They are perceptual-similarity candidates requiring human review. Possible explanations include:

- Resized or recompressed derivatives.
- Similar generated compositions or prompts.
- Repeated visual structure.
- Common source imagery.
- False positives from global dHash similarity.

dHash limitations:

- May miss crops, rotations, edits, overlays, and substantial transformations.
- May flag unrelated images with similar global gradients.
- Does not establish common provenance, prompt identity, generator identity, or leakage.
- It is not an embedding-based semantic similarity method.

## Verification and safety

- Protected snapshot was verified before the full run.
- Source manifest identity was checked against the snapshot metadata.
- All 10,000 manifest samples were included, including 4,000 unassigned rows.
- Existing outputs were protected from overwrite.
- Production manifest and images were not modified.
- Split assignments were not modified.
- Human-reviewed duplicate groups: **none recorded**.
- Confirmed cross-split leakage: **none established**.

## Recommended review sequence

1. Review the 45 assigned cross-split candidates first.
2. Review the 73 candidates involving unassigned rows before assigning any of those rows.
3. Group candidates into human-reviewed clusters.
4. Keep confirmed duplicate/derivative clusters in one future split.
5. Re-run a separate audit after review decisions are recorded.
