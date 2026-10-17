"""Deep dive investigation into generator-specific false negatives (flux.2-klein-9b, z-image-turbo, etc.)."""

from __future__ import annotations

import csv
import json
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np


def main() -> None:
    preds_path = Path("datasets/manifests/experiment_baseline_eval/per_sample_predictions.json")
    manifest_path = Path("datasets/manifests/dataset_manifest.csv")

    if not preds_path.is_file() or not manifest_path.is_file():
        print("Predictions or manifest not found.")
        return

    predictions = json.loads(preds_path.read_text(encoding="utf-8"))
    
    rows = []
    with manifest_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    manifest_map = {row["sample_id"]: row for row in rows}

    # Analyze score distributions by generator family for AI-generated images
    family_scores = defaultdict(list)
    family_fn_details = defaultdict(list)

    for p in predictions:
        if p["true_label"] == 1:
            gen = p["generator_family"]
            score = p["fake_probability"]
            family_scores[gen].append(score)
            if score < 0.20:
                family_fn_details[gen].append({
                    "sample_id": p["sample_id"],
                    "path": p["path"],
                    "score": score,
                })

    print("=== Generator Family Score Distributions (AI-Generated Test Samples, n=470) ===")
    summary = {}
    for gen, scores in sorted(family_scores.items(), key=lambda x: len(x[1]), reverse=True):
        arr = np.array(scores)
        mean_s = float(np.mean(arr))
        median_s = float(np.median(arr))
        min_s = float(np.min(arr))
        max_s = float(np.max(arr))
        fn_count_20 = sum(1 for s in scores if s < 0.20)
        fn_count_50 = sum(1 for s in scores if s < 0.50)
        tot = len(scores)
        
        summary[gen] = {
            "total": tot,
            "mean": round(mean_s, 4),
            "median": round(median_s, 4),
            "min": round(min_s, 4),
            "max": round(max_s, 4),
            "fn_at_0.20": fn_count_20,
            "recall_at_0.20": round((tot - fn_count_20) / tot, 4),
            "fn_at_0.50": fn_count_50,
            "recall_at_0.50": round((tot - fn_count_50) / tot, 4),
        }
        print(f"Family: {gen:<18} | n={tot:<3} | Mean: {mean_s:.4f} | Min: {min_s:.4f} | Max: {max_s:.4f} | Recall@0.20: {(tot - fn_count_20)/tot:.4f}")

    # Inspect flux.2-klein-9b specifically
    flux_scores = family_scores.get("flux.2-klein-9b", [])
    print(f"\nFlux.2-Klein-9b Analysis (n={len(flux_scores)}):")
    print(f"  Scores: {[round(s, 4) for s in flux_scores[:15]]} ...")

    out_dir = Path("datasets/manifests/experiment_generator_investigation")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "generator_error_summary.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nGenerator error summary saved to {out_path}")


if __name__ == "__main__":
    main()
