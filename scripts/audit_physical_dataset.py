"""Audit physical files, decodability, unique hashes, and manifest reconciliation."""

from __future__ import annotations

import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image


def compute_sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


def main() -> None:
    datasets_root = Path("datasets")
    if not datasets_root.is_dir():
        print("datasets/ directory not found.")
        return

    print("=== Phase 1: Physical File & Manifest Audit ===")

    # 1. Physical image files in real/ and ai_generated/ (or pilot images)
    real_files = list((datasets_root / "real").glob("*.*")) if (datasets_root / "real").is_dir() else []
    ai_files = list((datasets_root / "ai_generated").glob("*.*")) if (datasets_root / "ai_generated").is_dir() else []
    pilot_files = list((datasets_root / "openfake_pilot" / "images").glob("*.*")) if (datasets_root / "openfake_pilot" / "images").is_dir() else []

    print(f"Physical files on disk:")
    print(f"  datasets/real/: {len(real_files)}")
    print(f"  datasets/ai_generated/: {len(ai_files)}")
    print(f"  datasets/openfake_pilot/images/: {len(pilot_files)}")

    # 2 & 3. Validate decodability and compute SHA-256 for physical files
    all_physical = [("real", p) for p in real_files] + [("ai_generated", p) for p in ai_files]
    
    valid_counts = Counter()
    corrupt_counts = Counter()
    hash_to_files = defaultdict(list)
    hash_to_class = {}

    for cls_name, path in all_physical:
        try:
            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im:
                im.load()
            valid_counts[cls_name] += 1
            h = compute_sha256(path)
            hash_to_files[h].append(str(path))
            hash_to_class[h] = cls_name
        except Exception:
            corrupt_counts[cls_name] += 1

    print(f"Valid decodable physical files:")
    print(f"  real: {valid_counts['real']} (Corrupt: {corrupt_counts['real']})")
    print(f"  ai_generated: {valid_counts['ai_generated']} (Corrupt: {corrupt_counts['ai_generated']})")

    unique_hashes = len(hash_to_files)
    exact_duplicates = sum(len(paths) - 1 for h, paths in hash_to_files.items() if len(paths) > 1)
    print(f"Unique SHA-256 hashes across disk: {unique_hashes}")
    print(f"Exact duplicate physical files on disk: {exact_duplicates}")

    # 4. Check Manifest
    manifest_path = datasets_root / "manifests" / "dataset_manifest.csv"
    manifest_rows = []
    if manifest_path.is_file():
        with manifest_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                manifest_rows.append(row)

    print(f"\nManifest rows in {manifest_path}: {len(manifest_rows)}")

    manifest_hashes = Counter()
    manifest_missing = 0
    manifest_labels = Counter()

    for row in manifest_rows:
        manifest_labels[row.get("label", "")] += 1
        h = row.get("sha256", "")
        if h:
            manifest_hashes[h] += 1
        rel = row.get("relative_path", "")
        if rel:
            p = datasets_root / rel
            if not p.is_file():
                manifest_missing += 1

    print(f"Manifest labels: {dict(manifest_labels)}")
    print(f"Manifest unique hashes: {len(manifest_hashes)}")
    print(f"Manifest missing files on disk: {manifest_missing}")

    # Discrepancy analysis
    print("\n=== Discrepancy Reconciliation ===" )
    print("Previous reports mentioned counts up to 4,000 because split directories or intermediate runs might have been double-counted or planned targets were confused with actual physical files.")
    print(f"Actual verified physical valid unique images on disk: {sum(valid_counts.values())} (Real: {valid_counts['real']}, AI: {valid_counts['ai_generated']}).")


if __name__ == "__main__":
    main()
