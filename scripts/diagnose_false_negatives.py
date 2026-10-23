"""Diagnose false negatives and score distributions on the test split."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image

from backend.detector import get_detector


def main() -> None:
    manifest_path = Path("datasets/manifests/dataset_manifest.csv")
    if not manifest_path.is_file():
        print("Manifest not found.")
        return

    rows = []
    with manifest_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("split") == "test":
                rows.append(row)

    detector = get_detector()
    results = []

    for row in rows:
        img_path = Path("datasets") / row["relative_path"]
        label = row["label"]
        true_label = 1 if label == "ai_generated" else 0
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
                pred = 1 if score is not None and score >= 0.5 else 0
                correct = (pred == true_label)
                results.append({
                    "sample_id": row["sample_id"],
                    "path": row["relative_path"],
                    "label": label,
                    "true_label": true_label,
                    "generator_family": gen,
                    "score": score,
                    "prediction": pred,
                    "correct": correct,
                    "width": w,
                    "height": h,
                    "format": fmt,
                })
        except Exception as exc:
            print(f"Error on {img_path}: {exc}")

    # Analysis
    fn_samples = [r for r in results if r["true_label"] == 1 and not r["correct"]]
    tp_samples = [r for r in results if r["true_label"] == 1 and r["correct"]]
    fp_samples = [r for r in results if r["true_label"] == 0 and not r["correct"]]
    tn_samples = [r for r in results if r["true_label"] == 0 and r["correct"]]

    print(f"Total test samples evaluated: {len(results)}")
    print(f"TP: {len(tp_samples)}, FN: {len(fn_samples)}, FP: {len(fp_samples)}, TN: {len(tn_samples)}")

    print("\nFalse Negatives by Generator Family:")
    fn_generators = Counter(r["generator_family"] for r in fn_samples)
    for gen, count in fn_generators.most_common():
        print(f"  {gen}: {count}")

    print("\nFalse Negative Scores Summary:")
    fn_scores = [r["score"] for r in fn_samples if r["score"] is not None]
    if fn_scores:
        print(f"  Min: {min(fn_scores):.5f}, Max: {max(fn_scores):.5f}, Mean: {sum(fn_scores)/len(fn_scores):.5f}")

    print("\nTrue Positive Scores Summary:")
    tp_scores = [r["score"] for r in tp_samples if r["score"] is not None]
    if tp_scores:
        print(f"  Min: {min(tp_scores):.5f}, Max: {max(tp_scores):.5f}, Mean: {sum(tp_scores)/len(tp_scores):.5f}")

    print("\nReal (TN / FP) Scores Summary:")
    real_scores = [r["score"] for r in results if r["true_label"] == 0 and r["score"] is not None]
    if real_scores:
        print(f"  Min: {min(real_scores):.5f}, Max: {max(real_scores):.5f}, Mean: {sum(real_scores)/len(real_scores):.5f}")


if __name__ == "__main__":
    main()
