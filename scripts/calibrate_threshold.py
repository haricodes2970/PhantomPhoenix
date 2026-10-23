"""Threshold calibration script using validation split."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import numpy as np
from PIL import Image
from sklearn.metrics import precision_recall_fscore_support, accuracy_score, confusion_matrix

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
            if row.get("split") == "val":
                rows.append(row)

    print(f"Running threshold calibration on {len(rows)} validation samples...")
    detector = get_detector()

    y_true = []
    y_score = []

    for row in rows:
        img_path = Path("datasets") / row["relative_path"]
        label_str = row["label"]
        true_label = 1 if label_str == "ai_generated" else 0

        if not img_path.is_file():
            continue

        try:
            with Image.open(img_path) as img:
                rgb = img.convert("RGB")
                output = detector.infer(rgb)
            if output.fake_probability is not None:
                y_true.append(true_label)
                y_score.append(output.fake_probability)
        except Exception:
            pass

    y_arr = np.array(y_true)
    score_arr = np.array(y_score)

    thresholds = [0.50, 0.30, 0.20, 0.10, 0.05, 0.02, 0.01]
    results = []

    print(f"\n{'Threshold':<10} {'Accuracy':<10} {'Precision':<10} {'Recall':<10} {'F1':<10} {'FPR':<10}")
    print("-" * 65)

    for th in thresholds:
        pred_arr = np.array([1 if s >= th else 0 for s in score_arr])
        acc = float(accuracy_score(y_arr, pred_arr))
        prec, rec, f1, _ = precision_recall_fscore_support(y_arr, pred_arr, average="binary", zero_division=0)
        cm = confusion_matrix(y_arr, pred_arr, labels=[0, 1]).tolist()
        tn, fp, fn, tp = cm[0][0], cm[0][1], cm[1][0], cm[1][1]
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

        results.append({
            "threshold": th,
            "accuracy": round(acc, 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "fpr": round(fpr, 4),
            "confusion_matrix": cm,
        })
        print(f"{th:<10.2f} {acc:<10.4f} {float(prec):<10.4f} {float(rec):<10.4f} {float(f1):<10.4f} {fpr:<10.4f}")

    out_dir = Path("datasets/manifests/experiment_threshold_calibration")
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "calibration_summary.json"
    summary_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nCalibration summary saved to {summary_path}")


if __name__ == "__main__":
    main()