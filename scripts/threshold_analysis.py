"""Threshold and calibration analysis using validation split only."""

from __future__ import annotations

import csv
from pathlib import Path
from PIL import Image
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score, confusion_matrix

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
            if row.get("split") == "val":
                rows.append(row)

    detector = get_detector()
    y_true = []
    y_score = []

    for row in rows:
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

    print(f"Validation samples evaluated: {len(y_true)}")
    print(f"  Real: {sum(1 for y in y_true if y == 0)}, AI: {sum(1 for y in y_true if y == 1)}")

    print("\nThreshold Sweep on Validation Split:")
    print(f"{'Threshold':<10} | {'Accuracy':<10} | {'Precision':<10} | {'Recall':<10} | {'F1':<10} | {'CM [[TN,FP],[FN,TP]]'}")
    print("-" * 75)

    best_t = 0.5
    best_f1 = -1.0

    for t in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        y_pred = [1 if s >= t else 0 for s in y_score]
        acc = accuracy_score(y_true, y_pred)
        prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist()
        if f1 > best_f1:
            best_f1 = f1
            best_t = t
        print(f"{t:<10.1f} | {acc:<10.4f} | {prec:<10.4f} | {rec:<10.4f} | {f1:<10.4f} | {cm}")

    print(f"\nBest validation threshold by F1: {best_t} (F1: {best_f1:.4f})")
    print("NOTE: Production policy remains 0.80 likely_ai / 0.20 likely_real per backend config. This validation sweep is exploratory only.")


if __name__ == "__main__":
    main()
