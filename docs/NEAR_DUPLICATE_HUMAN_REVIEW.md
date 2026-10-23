# Near-Duplicate Human Review Workflow

**Date:** 2026-10-20  
**Candidates:** 97 perceptual-similarity candidates  
**Status:** All candidates remain `pending` / `unreviewed`

## Readiness validation

Verified before preparation:

- Candidate JSON and CSV contain the same 97 pairs.
- Candidate IDs are unique and stable.
- All sample IDs exist in the current manifest.
- Candidate hashes match manifest hashes.
- dHash distances are within configured threshold.
- Cross-split flags are consistent with manifest splits.
- Source manifest hash matches protected snapshot metadata.
- Review HTML exists and references local dataset paths.
- Existing queue contains 97 rows, all with blank reviewer decisions.
- No candidate is marked confirmed leakage.

Current prioritization counts:

- Assigned cross-split candidates: 45 total, including 0 with unassigned involvement.
- Assigned/unassigned candidates: 73 total.
- Remaining candidates: included in the queue and priority view.

These categories overlap by design. Priority indicates review order, not leakage probability.

## Review artifacts

Original queue preserved:

```text
datasets/provenance/near_duplicate_review_v1/near_duplicate_review_queue_v1.csv
```

Original local review page preserved:

```text
datasets/provenance/near_duplicate_review_v1/index.html
```

New deterministic priority view:

```text
datasets/provenance/near_duplicate_review_v1/review_priority_v1.csv
```

Open local review page:

```bash
xdg-open datasets/provenance/near_duplicate_review_v1/index.html
```

No network requests or uploads are required.

## Review order

1. Assigned train/validation/test boundary candidates.
2. Candidates connecting assigned and unassigned samples.
3. Candidates with smallest dHash distance.
4. Remaining candidates by stable candidate ID.

Priority does not imply that a candidate is a confirmed duplicate.

## Reviewer workflow

For each pair:

1. Open `index.html` locally.
2. Compare both images at the same viewing scale.
3. Check dimensions, composition, visible crops, recompression, resizing, overlays, and other transformation clues.
4. Do not infer shared provenance from style, subject, composition, or generator-family labels alone.
5. Record a decision only when visual evidence supports it.
6. Record reviewer identity, UTC date, and concise rationale.
7. Use `uncertain` when evidence is insufficient.
8. Leave `unreviewed` when no inspection occurred.

Allowed decisions:

- `same_image_transform`: strong evidence the same image was resized, recompressed, or minimally transformed.
- `near_duplicate_related`: related derivative, but not clearly the same image.
- `visually_similar_unrelated`: similar appearance without enough same-image evidence.
- `uncertain`: insufficient evidence.
- `unreviewed`: not inspected.

## Review record validation

Validate a completed copy without modifying the production queue or manifest:

```bash
PYTHONPATH=. .venv/bin/python scripts/validate_near_duplicate_review.py \
  datasets/provenance/near_duplicate_review_v1/near_duplicate_review_queue_v1.csv
```

Reviewed decisions require:

- Valid decision value.
- Reviewer identity.
- UTC review date.
- Reviewer notes.
- Existing candidate IDs and hashes unchanged.

The validator does not write files.

## Integrity rules

- Never edit the production manifest during review.
- Never assign or move samples based only on dHash similarity.
- Never call a candidate confirmed leakage without adequate human evidence.
- Preserve the original candidate queue as the audit input.
- Create a separately named reviewed copy if project lead approves review recording.
