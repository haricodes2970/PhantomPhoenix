"""Validate a human-edited near-duplicate review queue without overwriting it."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

DECISIONS = {
    "same_image_transform",
    "near_duplicate_related",
    "visually_similar_unrelated",
    "uncertain",
    "unreviewed",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("queue", type=Path)
    parser.add_argument("--manifest", type=Path, default=Path("datasets/manifests/dataset_manifest.csv"))
    parser.add_argument("--protected-metadata", type=Path, default=Path("datasets/provenance/protected_dataset_snapshot.json"))
    args = parser.parse_args(argv)
    metadata = json.loads(args.protected_metadata.read_text(encoding="utf-8"))
    if sha256_file(args.manifest) != metadata.get("source_manifest_sha256"):
        print("source manifest differs from protected snapshot")
        return 3
    rows = {row["sample_id"]: row for row in csv.DictReader(args.manifest.open(encoding="utf-8", newline=""))}
    errors: list[str] = []
    with args.queue.open(encoding="utf-8", newline="") as handle:
        queue = list(csv.DictReader(handle))
    ids: set[str] = set()
    for index, item in enumerate(queue, start=2):
        candidate_id = item.get("candidate_id", "")
        if not candidate_id or candidate_id in ids:
            errors.append(f"row {index}: duplicate or missing candidate_id")
        ids.add(candidate_id)
        decision = item.get("reviewer_decision", "") or "unreviewed"
        if decision not in DECISIONS:
            errors.append(f"row {index}: invalid decision {decision!r}")
        reviewed = decision != "unreviewed"
        required = ("reviewer", "review_date_utc", "reviewer_notes")
        if reviewed and any(not item.get(field, "").strip() for field in required):
            errors.append(f"row {index}: reviewed decision requires reviewer, date, and notes")
        for side in ("a", "b"):
            sample_id = item.get(f"sample_{side}", "")
            if sample_id not in rows:
                errors.append(f"row {index}: unknown sample {sample_id}")
            elif item.get(f"sha256_{side}") != rows[sample_id].get("sha256"):
                errors.append(f"row {index}: hash mismatch for {sample_id}")
    if errors:
        print("review validation failed")
        for error in errors[:100]: print(error)
        return 1
    print(f"validated {len(queue)} review rows; decisions={sum((x.get('reviewer_decision') or 'unreviewed') != 'unreviewed' for x in queue)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
