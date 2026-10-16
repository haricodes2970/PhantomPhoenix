"""Build non-destructive metadata manifest and analyze dataset-source confounding."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS


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

    metadata_records = []
    for row in rows:
        img_path = Path("datasets") / row["relative_path"]
        rec = {
            "sample_id": row["sample_id"],
            "sha256": row["sha256"],
            "label": row["label"],
            "generator_family": row["generator_family"],
            "original_dataset": row["original_dataset"],
            "split": row["split"],
            "width": None,
            "height": None,
            "aspect_ratio": None,
            "format": None,
            "file_size_bytes": None,
            "has_exif": False,
        }

        if img_path.is_file():
            rec["file_size_bytes"] = img_path.stat().st_size
            try:
                with Image.open(img_path) as img:
                    w, h = img.size
                    rec["width"] = w
                    rec["height"] = h
                    rec["aspect_ratio"] = round(w / h, 4) if h > 0 else 0.0
                    rec["format"] = img.format or "UNKNOWN"
                    exif = img.getexif()
                    rec["has_exif"] = len(exif) > 0 if exif else False
            except Exception as exc:
                rec["error"] = str(exc)
        metadata_records.append(rec)

    out_dir = Path("datasets/provenance")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "metadata_audit_record.json"

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(metadata_records, f, indent=2)

    print(f"Metadata audit record written to {out_path} ({len(metadata_records)} records)")

    # Summary statistics
    formats = Counter(r["format"] for r in metadata_records)
    exif_count = sum(1 for r in metadata_records if r["has_exif"])
    print(f"Formats: {dict(formats)}")
    print(f"EXIF present: {exif_count}/{len(metadata_records)}")


if __name__ == "__main__":
    import sys
    from collections import Counter
    main()
