"""Dataset quality and attribution distribution audit script."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image


def main() -> None:
    manifest_path = Path("datasets/manifests/dataset_manifest.csv")
    if not manifest_path.is_file():
        print(f"Manifest not found: {manifest_path}")
        return

    rows = []
    with manifest_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    print(f"Total manifest rows: {len(rows)}")

    labels = Counter()
    sources = Counter()
    generators = Counter()
    formats = Counter()
    splits = Counter()
    split_class = defaultdict(Counter)
    resolutions = Counter()

    missing = 0
    hashes = []

    for row in rows:
        labels[row.get("label", "unknown")] += 1
        sources[row.get("original_dataset", "unknown")] += 1
        generators[row.get("generator_family", "unknown")] += 1
        formats[row.get("original_format", "unknown")] += 1
        s = row.get("split", "unassigned")
        splits[s] += 1
        split_class[s][row.get("label", "unknown")] += 1

        h = row.get("sha256", "")
        if h:
            hashes.append(h)

        rel = row.get("relative_path", "")
        if rel:
            img_path = Path("datasets") / rel
            if not img_path.is_file():
                missing += 1
            else:
                try:
                    with Image.open(img_path) as im:
                        w, h_dim = im.size
                        resolutions[f"{w}x{h_dim}"] += 1
                except Exception:
                    pass

    unique_hashes = len(set(hashes))
    duplicate_hashes = len(hashes) - unique_hashes

    print(f"\n--- Audit Findings ---")
    print(f"Missing physical files: {missing}")
    print(f"Unique SHA-256 hashes: {unique_hashes} (Duplicates: {duplicate_hashes})")
    print(f"Labels: {dict(labels)}")
    print(f"Sources: {dict(sources)}")
    print(f"Generators (Top 10): {dict(generators.most_common(10))}")
    print(f"Original Formats: {dict(formats)}")
    print(f"Splits: {dict(splits)}")
    for sp, counts in split_class.items():
        print(f"  Split {sp}: {dict(counts)}")
    print(f"Top 10 Resolutions: {dict(resolutions.most_common(10))}")


if __name__ == "__main__":
    main()
