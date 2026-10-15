"""Robust dataset acquisition and preparation pipeline for 1,000 images (500 real, 500 AI-generated)."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image
from datasets import load_dataset


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare PHANTOM PHOENIX research dataset (1,000 images).")
    parser.add_argument("--target-real", type=int, default=500, help="Target number of real photographs (default: 500)")
    parser.add_argument("--target-ai", type=int, default=500, help="Target number of AI-generated images (default: 500)")
    parser.add_argument("--max-scans", type=int, default=10000, help="Maximum rows to stream from dataset source (default: 10000)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling (default: 42)")
    parser.add_argument("--dataset-name", type=str, default="ComplexDataLab/OpenFake", help="Hugging Face dataset name")
    parser.add_argument("--dataset-config", type=str, default="core", help="Dataset configuration")
    parser.add_argument("--dataset-split", type=str, default="test", help="Dataset split")
    parser.add_argument("--output-dir", type=Path, default=Path("datasets"), help="Root dataset directory")
    args = parser.parse_args()

    output_dir: Path = Path(args.output_dir)
    real_dir = output_dir / "real"
    ai_dir = output_dir / "ai_generated"
    manifests_dir = output_dir / "manifests"
    provenance_dir = output_dir / "provenance"
    eval_manifests_dir = output_dir / "evaluation" / "manifests"

    for d in (real_dir, ai_dir, manifests_dir, provenance_dir, eval_manifests_dir):
        d.mkdir(parents=True, exist_ok=True)

    manifest_path = manifests_dir / "dataset_manifest.csv"
    summary_path = manifests_dir / "acquisition_summary.json"
    provenance_path = provenance_dir / "openfake_provenance.json"
    readme_path = output_dir / "README.md"

    random.seed(args.seed)

    print(f"Streaming {args.dataset_name} ({args.dataset_config}/{args.dataset_split})...")
    try:
        ds = load_dataset(
            args.dataset_name,
            name=args.dataset_config,
            split=args.dataset_split,
            streaming=True,
        )
    except Exception as exc:
        print(f"Error streaming dataset: {exc}", file=sys.stderr)
        sys.exit(1)

    real_collected = 0
    ai_collected = 0
    scanned = 0
    duplicates_rejected = 0
    corrupt_rejected = 0
    exclusions: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()

    # Load existing manifest if resuming
    if manifest_path.is_file():
        try:
            with manifest_path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    h = row.get("sha256", "")
                    if h:
                        seen_hashes.add(h)
                    if row.get("label") == "real":
                        real_collected += 1
                    elif row.get("label") == "ai_generated":
                        ai_collected += 1
                    manifest_rows.append(row)
            print(f"Resumed from existing manifest: {real_collected} real, {ai_collected} AI-generated already collected.")
        except Exception as exc:
            print(f"Warning: failed to load existing manifest: {exc}", file=sys.stderr)

    print(f"Scanning up to {args.max_scans} rows to collect {args.target_real} real and {args.target_ai} AI-generated images...")

    for row in ds:
        scanned += 1
        if scanned > args.max_scans:
            print(f"Reached max scan limit ({args.max_scans}). Stopping.")
            break

        raw_label = str(row.get("label", "")).strip().lower()
        if raw_label not in ("real", "fake"):
            exclusions.append({"scanned_index": scanned, "reason": f"Unknown label: {raw_label}"})
            continue

        label = "real" if raw_label == "real" else "ai_generated"

        if label == "real" and real_collected >= args.target_real:
            continue
        if label == "ai_generated" and ai_collected >= args.target_ai:
            continue

        image = row.get("image")
        if image is None:
            exclusions.append({"scanned_index": scanned, "reason": "Image missing from row"})
            continue

        try:
            # Export to bytes for hashing and integrity check
            img_format = image.format or "JPEG"
            ext = img_format.lower()
            if ext == "jpeg":
                ext = "jpg"

            buffer = sys.modules["io"].BytesIO() if "io" in sys.modules else None
            import io
            buf = io.BytesIO()
            # Save in original format or fallback to JPEG
            save_format = image.format if image.format in ("JPEG", "PNG", "WEBP") else "JPEG"
            if save_format == "JPEG":
                image.convert("RGB").save(buf, format="JPEG", quality=95)
                ext = "jpg"
            elif save_format == "PNG":
                image.convert("RGB").save(buf, format="PNG")
                ext = "png"
            else:
                save_format = "JPEG"
                image.convert("RGB").save(buf, format="JPEG", quality=95)
                ext = "jpg"

            img_bytes = buf.getvalue()
            file_sha256 = compute_sha256(img_bytes)

            if file_sha256 in seen_hashes:
                duplicates_rejected += 1
                continue

            # Verify image decode integrity
            try:
                with Image.open(io.BytesIO(img_bytes)) as test_img:
                    test_img.verify()
                with Image.open(io.BytesIO(img_bytes)) as test_img:
                    test_img.load()
                    width, height = test_img.size
            except Exception as img_exc:
                corrupt_rejected += 1
                exclusions.append({"scanned_index": scanned, "reason": f"Corrupt image decode failed: {img_exc}"})
                continue

            # Assign deterministic unique filename and path
            if label == "real":
                real_collected += 1
                sample_id = f"real_{real_collected:06d}"
                rel_path = f"real/{sample_id}.{ext}"
                dest_path = real_dir / f"{sample_id}.{ext}"
            else:
                ai_collected += 1
                sample_id = f"ai_{ai_collected:06d}"
                rel_path = f"ai_generated/{sample_id}.{ext}"
                dest_path = ai_dir / f"{sample_id}.{ext}"

            dest_path.write_bytes(img_bytes)
            seen_hashes.add(file_sha256)

            generator_family = str(row.get("model", "")).strip() or "UNKNOWN"
            original_sample_id = str(row.get("id", "")).strip() or str(scanned)

            manifest_rows.append({
                "sample_id": sample_id,
                "relative_path": rel_path,
                "label": label,
                "original_dataset": args.dataset_name,
                "original_revision": args.dataset_config,
                "original_sample_id": original_sample_id,
                "generator_family": generator_family,
                "original_format": save_format,
                "sha256": file_sha256,
                "license_ref": "CC BY-NC 4.0",
                "download_status": "success",
                "split": "unassigned",
            })

            print(f"[{real_collected + ai_collected}/{args.target_real + args.target_ai}] Saved {label}: {sample_id} ({generator_family})")

            if real_collected >= args.target_real and ai_collected >= args.target_ai:
                print("Target counts reached for both classes.")
                break

        except Exception as exc:
            exclusions.append({"scanned_index": scanned, "reason": f"Processing exception: {exc}"})

    # Write dataset manifest CSV
    fieldnames = [
        "sample_id",
        "relative_path",
        "label",
        "original_dataset",
        "original_revision",
        "original_sample_id",
        "generator_family",
        "original_format",
        "sha256",
        "license_ref",
        "download_status",
        "split",
    ]
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manifest_rows)

    # Write acquisition summary JSON
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "target_real": args.target_real,
        "target_ai": args.target_ai,
        "collected_real": real_collected,
        "collected_ai": ai_collected,
        "total_collected": real_collected + ai_collected,
        "scanned_rows": scanned,
        "duplicates_rejected": duplicates_rejected,
        "corrupt_rejected": corrupt_rejected,
        "exclusions_count": len(exclusions),
        "exclusions": exclusions,
    }
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Write provenance record
    provenance = {
        "dataset_source": args.dataset_name,
        "config": args.dataset_config,
        "split": args.dataset_split,
        "license": "CC BY-NC 4.0",
        "attribution": "ComplexDataLab/OpenFake (CC BY-NC 4.0 - Non-commercial research use only)",
        "retrieval_timestamp": summary["timestamp"],
        "random_seed": args.seed,
    }
    with provenance_path.open("w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)

    # Write datasets README
    readme_content = f"""# PHANTOM PHOENIX Research Dataset

- **Target Size:** 1,000 images (500 real photographs, 500 AI-generated images)
- **Source:** Hugging Face `{args.dataset_name}` (`{args.dataset_config}` config, `{args.dataset_split}` split)
- **License:** CC BY-NC 4.0 (Non-commercial research use only)
- **Acquisition Timestamp:** {summary["timestamp"]}
- **Collected Counts:** {real_collected} real, {ai_collected} AI-generated (Total: {real_collected + ai_collected})
- **Manifest:** `manifests/dataset_manifest.csv`
- **Summary:** `manifests/acquisition_summary.json`
- **Provenance:** `provenance/openfake_provenance.json`

## Directory Structure
- `real/`: Real photographs (`real_000001.jpg`, ...)
- `ai_generated/`: AI-generated images (`ai_000001.jpg`, ...)
- `manifests/`: Dataset manifest and acquisition metrics
- `provenance/`: Dataset license and source provenance records

## Limitations & Licensing
This dataset is acquired under CC BY-NC 4.0 for non-commercial AI detection research and evaluation. It must not be used for commercial purposes.
"""
    with readme_path.open("w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"\nDataset acquisition pipeline complete!")
    print(f"Manifest: {manifest_path}")
    print(f"Summary: {summary_path}")
    print(f"Collected: {real_collected} real, {ai_collected} AI-generated.")


if __name__ == "__main__":
    main()
