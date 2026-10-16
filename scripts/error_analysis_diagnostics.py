"""Produce sample-level error diagnostics CSV and error summaries by generator family and format."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image

from backend.detector import get_detector


def main() -> None:
    manifest_path = Path("datasets/manifests/dataset_manifest.csv")
    if not manifest_path.is_file():
        print(f"Manifest not found: {manifest_path}")
        return

    rows = []
    with manifest_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("split") == "test":
                rows.append(row)

    print(f"Running error diagnostics on {len(rows)} test samples...")
    detector = get_detector()
    threshold = 0.50

    diagnostics = []
    fn_by_generator = Counter()
    fp_by_generator = Counter()

    for row in rows:
        img_path = Path("datasets") / row["relative_path"]
        label_str = row["label"]
        true_label = 1 if label_str == "ai_generated" else 0
        gen = row["generator_family"]

        if not img_path.is_file():
            continue

        try:
            with Image.open(img_path) as img:
                rgb = img.convert("RGB")
                w, h = rgb.size
                fmt = img.format or "UNKNOWN"
                output = detector.infer(rgb)
                score = output.fake_probability
                if score is None:
                    continue
                pred = 1 if score >= threshold else 0
                correct = (pred == true_label)

                category = "TN"
                if true_label == 1 and correct:
                    category = "TP"
                elif true_label == 1 and not correct:
                    category = "FN"
                    fn_by_generator[gen] += 1
                elif true_label == 0 and not correct:
                    category = "FP"
                    fp_by_generator[gen] += 1
                else:
                    category = "TN"

                diagnostics.append({
                    "sample_id": row["sample_id"],
                    "relative_path": row["relative_path"],
                    "label": label_str,
                    "true_label": true_label,
                    "generator_family": gen,
                    "score": round(score, 6),
                    "prediction": pred,
                    "correct": correct,
                    "error_category": category,
                    "width": w,
                    "height": h,
                    "format": fmt,
                })
        except Exception as exc:
            pass

    out_dir = Path("datasets/manifests/experiment_error_analysis")
    out_dir.mkdir(parents=True, exist_ok=True)
    diag_csv = out_dir / "sample_error_diagnostics.csv"

    fieldnames = [
        "sample_id", "relative_path", "label", "true_label", "generator_family",
        "score", "prediction", "correct", "error_category", "width", "height", "format"
    ]
    with diag_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(diagnostics)

    print(f"Sample-level error diagnostics CSV written to {diag_csv} ({len(diagnostics)} records)")
    print("\nFalse Negatives by Generator Family (Test Split):")
    for gen, count in fn_by_generator.most_common():
        print(f"  {gen}: {count}")

    print("\nFalse Positives by Generator Family (Test Split):")
    for gen, count in fp_by_generator.most_common():
        print(f"  {gen}: {count}")


if __name__ == "__main__":
    main()
