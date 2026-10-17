"""Validate FLUX.2-Klein-9B score distributions, metadata characteristics, and preprocessing parameters."""

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

    flux_samples = []
    other_ai_samples = []

    for p in predictions:
        if p["true_label"] == 1:
            m_row = manifest_map.get(p["sample_id"], {})
            img_path = Path("datasets") / p["path"]
            file_size = img_path.stat().st_size if img_path.is_file() else 0
            
            item = {
                **p,
                "file_size": file_size,
            }
            if p["generator_family"] == "flux.2-klein-9b":
                flux_samples.append(item)
            else:
                other_ai_samples.append(item)

    print(f"Total FLUX test samples: {len(flux_samples)}")
    flux_scores = [s["fake_probability"] for s in flux_samples]
    print(f"  FLUX Mean Score: {np.mean(flux_scores):.5f}")
    print(f"  FLUX Min Score:  {min(flux_scores):.5f}")
    print(f"  FLUX Max Score:  {max(flux_scores):.5f}")
    print(f"  FLUX TP @ 0.50:  {sum(1 for s in flux_samples if s['fake_probability'] >= 0.50)}")
    print(f"  FLUX TP @ 0.20:  {sum(1 for s in flux_samples if s['fake_probability'] >= 0.20)}")

    # Check file sizes and resolutions for FLUX vs others
    flux_sizes = [s["file_size"] for s in flux_samples]
    other_sizes = [s["file_size"] for s in other_ai_samples]

    summary = {
        "flux_count": len(flux_samples),
        "flux_score_mean": round(float(np.mean(flux_scores)), 5),
        "flux_score_min": round(float(min(flux_scores)), 5),
        "flux_score_max": round(float(max(flux_scores)), 5),
        "flux_tp_at_0.50": sum(1 for s in flux_samples if s['fake_probability'] >= 0.50),
        "flux_tp_at_0.20": sum(1 for s in flux_samples if s['fake_probability'] >= 0.20),
        "flux_mean_file_size": round(float(np.mean(flux_sizes)), 2) if flux_sizes else 0,
        "other_ai_mean_file_size": round(float(np.mean(other_sizes)), 2) if other_sizes else 0,
    }

    out_dir = Path("datasets/manifests/experiment_flux_validation")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "flux_validation_summary.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nFlux validation summary saved to {out_path}")


if __name__ == "__main__":
    main()
