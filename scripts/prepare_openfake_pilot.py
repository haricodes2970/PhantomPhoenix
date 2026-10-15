"""Script to prepare a small pilot evaluation dataset from Hugging Face ComplexDataLab/OpenFake."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from datasets import load_dataset


def main() -> None:
    output_dir = Path("datasets/openfake_pilot")
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / "eval_manifest.csv"
    provenance_path = output_dir / "provenance.json"
    readme_path = output_dir / "README.md"

    target_real = 25
    target_fake = 25
    max_scans = 1000  # Stop after scanning 1000 rows max

    print(f"Streaming ComplexDataLab/OpenFake (core/test split)...")
    try:
        ds = load_dataset(
            "ComplexDataLab/OpenFake",
            name="core",
            split="test",
            streaming=True,
        )
    except Exception as exc:
        print(f"Error streaming dataset: {exc}", file=sys.stderr)
        sys.exit(1)

    real_collected = 0
    fake_collected = 0
    scanned = 0
    exclusions = []
    manifest_rows = []

    print(f"Scanning up to {max_scans} rows to collect {target_real} real and {target_fake} fake images...")

    for row in ds:
        scanned += 1
        if scanned > max_scans:
            print(f"Reached max scan limit ({max_scans}). Stopping.")
            break

        label = str(row.get("label", "")).strip().lower()
        if label not in ("real", "fake"):
            exclusions.append({"index": scanned, "reason": f"Unknown label: {label}"})
            continue

        if label == "real" and real_collected >= target_real:
            continue
        if label == "fake" and fake_collected >= target_fake:
            continue

        image = row.get("image")
        if image is None:
            exclusions.append({"index": scanned, "reason": "Image missing"})
            continue

        try:
            # Save image
            file_ext = "jpg"
            if image.format:
                file_ext = image.format.lower()
                if file_ext == "jpeg":
                    file_ext = "jpg"

            filename = f"{label}_{real_collected + fake_collected + 1:03d}.{file_ext}"
            img_path = images_dir / filename
            image.convert("RGB").save(img_path, quality=95)

            # Map label for backend/evaluation.py
            eval_label = "real" if label == "real" else "fake"

            manifest_rows.append({
                "path": str(img_path.resolve()),
                "label": eval_label,
                "source_model": row.get("model", ""),
                "source_type": row.get("type", ""),
                "release_date": row.get("release_date", ""),
            })

            if label == "real":
                real_collected += 1
            else:
                fake_collected += 1

            print(f"[{real_collected + fake_collected}/{target_real + target_fake}] Collected {label}: {filename}")

            if real_collected >= target_real and fake_collected >= target_fake:
                print("Target counts reached for both classes.")
                break

        except Exception as exc:
            exclusions.append({"index": scanned, "reason": f"Failed to save image: {exc}"})

    # Write manifest CSV
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "label", "source_model", "source_type", "release_date"])
        writer.writeheader()
        writer.writerows(manifest_rows)

    # Write provenance JSON
    provenance = {
        "dataset_source": "ComplexDataLab/OpenFake",
        "config": "core",
        "split": "test",
        "license": "CC BY-NC 4.0",
        "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
        "sampling_method": f"Streamed first {scanned} rows, sampled up to {target_real} real and {target_fake} fake images.",
        "selected_real_count": real_collected,
        "selected_fake_count": fake_collected,
        "total_selected": real_collected + fake_collected,
        "scanned_rows": scanned,
        "exclusions_count": len(exclusions),
        "exclusions": exclusions,
    }
    with provenance_path.open("w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)

    # Write README
    readme_content = f"""# OpenFake Pilot Evaluation Dataset

- **Source:** Hugging Face `ComplexDataLab/OpenFake` (`core` config, `test` split)
- **License:** CC BY-NC 4.0 (Non-commercial research use only)
- **Retrieval Timestamp:** {provenance["retrieval_timestamp"]}
- **Selected Counts:** {real_collected} real, {fake_collected} fake (Total: {real_collected + fake_collected})
- **Manifest:** `eval_manifest.csv`
- **Provenance Record:** `provenance.json`
- **Images Directory:** `images/`

## Limitations & Attribution
This dataset is a small pilot subset sampled from the OpenFake benchmark to validate the `DetectorEvaluator` ingestion workflow. It is NOT intended or sufficient for claiming general detector accuracy.
"""
    with readme_path.open("w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"\nPilot dataset preparation complete!")
    print(f"Manifest: {manifest_path}")
    print(f"Provenance: {provenance_path}")
    print(f"Total images saved: {real_collected + fake_collected}")


if __name__ == "__main__":
    main()
