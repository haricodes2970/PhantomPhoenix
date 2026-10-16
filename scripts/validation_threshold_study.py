"""Validation-only threshold sweep and calibration study using the validation split (890 samples)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import numpy as np
from PIL import Image
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

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

    print(f"Loaded {len(rows)} validation samples from {manifest_path}")
    detector = get_detector()

    y_true = []
    y_score = []

    for i, row in enumerate(rows):
        img_path = Path("datasets") / row["relative_path"]
        true_label = 1 if row["label"] == "ai_generated" else 0
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

    if not y_true:
        print("No valid validation samples.")
        return

    y_arr = np.array(y_true)
    score_arr = np.array(y_score)

    thresholds = [round(x * 0.05, 2) for x in range(1, 20)]
    sweep_results = []

    print("\nValidation Threshold Sweep (n = 890):")
    print(f"{'Threshold':<10} | {'Accuracy':<10} | {'Precision':<10} | {'Recall':<10} | {'F1':<10} | {'FPR':<10} | {'FNR':<10} | {'CM [[TN,FP],[FN,TP]]'}")
    print("-" * 100)

    best_t = 0.50
    best_f1 = -1.0

    for t in thresholds:
        pred_arr = np.array([1 if s >= t else 0 for s in score_arr])
        acc = float(accuracy_score(y_arr, pred_arr))
        prec, rec, f1, _ = precision_recall_fscore_support(y_arr, pred_arr, average="binary", zero_division=0)
        cm = confusion_matrix(y_arr, pred_arr, labels=[0, 1]).tolist()
        tn, fp, fn, tp = cm[0][0], cm[0][1], cm[1][0], cm[1][1]
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

        if f1 > best_f1:
            best_f1 = f1
            best_t = t

        res = {
            "threshold": t,
            "accuracy": round(acc, 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "fpr": round(fpr, 4),
            "fnr": round(fnr, 4),
            "confusion_matrix": cm,
        }
        sweep_results.append(res)
        print(f"{t:<10.2f} | {acc:<10.4f} | {float(prec):<10.4f} | {float(rec):<10.4f} | {float(f1):<10.4f} | {fpr:<10.4f} | {fnr:<10.4f} | {cm}")

    print(f"\nBest validation threshold by F1: {best_t:.2f} (F1: {best_f1:.4f})")

    out_dir = Path("datasets/manifests/experiment_error_analysis")
    out_dir.mkdir(parents=True, exist_ok=True)
    sweep_path = out_dir / "validation_threshold_sweep.json"
    sweep_path.write_text(json.dumps(sweep_results, indent=2), encoding="utf-8")
    print(f"Validation threshold sweep saved to {sweep_path}")


if __name__ == "__main__":
    main()
