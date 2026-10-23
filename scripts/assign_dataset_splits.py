"""Assign train, validation, and test splits (70/15/15) with strict leakage prevention."""

from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Assign dataset splits with leakage prevention.")
    parser.add_argument("--manifest", type=Path, default=Path("datasets/manifests/dataset_manifest.csv"), help="Path to dataset manifest CSV")
    parser.add_argument("--train-ratio", type=float, default=0.70, help="Training split ratio")
    parser.add_argument("--val-ratio", type=float, default=0.15, help="Validation split ratio")
    parser.add_argument("--test-ratio", type=float, default=0.15, help="Test split ratio")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for splitting")
    args = parser.parse_args()

    manifest_path: Path = args.manifest
    if not manifest_path.is_file():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    rows = []
    with manifest_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    random.seed(args.seed)

    # Group rows by (label, generator_family) to achieve stratified splitting
    strata: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (row["label"], row["generator_family"])
        strata[key].append(row)

    updated_rows = []
    seen_hashes: set[str] = set()

    for key, group in strata.items():
        random.shuffle(group)
        n = len(group)
        n_train = int(n * args.train_ratio)
        n_val = int(n * args.val_ratio)

        for i, row in enumerate(group):
            # Check SHA-256 leakage across splits
            h = row["sha256"]
            if h in seen_hashes:
                print(f"WARNING: Duplicate SHA-256 detected: {h} for sample {row['sample_id']}")
            seen_hashes.add(h)

            if i < n_train:
                row["split"] = "train"
            elif i < n_train + n_val:
                row["split"] = "val"
            else:
                row["split"] = "test"
            updated_rows.append(row)

    # Write back updated manifest
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    # Summary counts per split
    split_counts = defaultdict(lambda: defaultdict(int))
    for row in updated_rows:
        split_counts[row["split"]][row["label"]] += 1

    print("Dataset split assignment complete!")
    for split, counts in sorted(split_counts.items()):
        print(f"  Split: {split:<6} | real: {counts['real']:<3} | ai_generated: {counts['ai_generated']:<3} | total: {sum(counts.values())}")


if __name__ == "__main__":
    import sys
    main()
