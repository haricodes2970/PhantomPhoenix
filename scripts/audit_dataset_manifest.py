"""Audit dataset manifests, splits, integrity, and provenance."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image


def audit_manifest(manifest_path: Path, image_root: Path) -> None:
    print(f"\n=== Auditing Manifest: {manifest_path} ===")
    if not manifest_path.is_file():
        print(f"Manifest not found: {manifest_path}")
        return

    rows = []
    with manifest_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    print(f"Total rows: {len(rows)}")

    hashes = []
    missing_files = 0
    corrupt_files = 0
    labels = Counter()
    generators = Counter()
    splits = Counter()
    split_class = defaultdict(Counter)

    for row in rows:
        labels[row.get("label", "unknown")] += 1
        generators[row.get("generator_family", "unknown")] += 1
        s = row.get("split", "unassigned")
        splits[s] += 1
        split_class[s][row.get("label", "unknown")] += 1

        h = row.get("sha256", "")
        if h:
            hashes.append(h)

        rel = row.get("relative_path") or row.get("path")
        if rel:
            img_path = Path(rel)
            if not img_path.is_absolute():
                img_path = image_root / rel
            if not img_path.is_file():
                missing_files += 1
            else:
                try:
                    with Image.open(img_path) as im:
                        im.verify()
                    with Image.open(img_path) as im:
                        im.load()
                except Exception:
                    corrupt_files += 1

    unique_hashes = len(set(hashes))
    duplicate_hashes = len(hashes) - unique_hashes

    print(f"Unique SHA-256 hashes: {unique_hashes} (Duplicates: {duplicate_hashes})")
    print(f"Missing files: {missing_files}")
    print(f"Corrupt/unreadable files: {corrupt_files}")
    print(f"Labels: {dict(labels)}")
    print(f"Generators: {dict(generators)}")
    print(f"Splits: {dict(splits)}")
    for sp, counts in split_class.items():
        print(f"  Split {sp}: {dict(counts)}")


def main() -> None:
    audit_manifest(Path("datasets/manifests/dataset_manifest.csv"), Path("datasets"))
    audit_manifest(Path("datasets/openfake_pilot/eval_manifest.csv"), Path(" datasets/openfake_pilot/images"))


if __name__ == "__main__":
    main()
