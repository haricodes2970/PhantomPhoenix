"""Evaluate baseline detector on the held-out test split of the research dataset."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import numpy as np
from PIL import Image
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score, confusion_matrix

from backend.detector import get_detector


def main() -> None:
    manifest_path = Path("datasets/manifests/dataset_manifest.csv")
    if not manifest_path.is_file():
        print(f"Dataset manifest not found: {manifest_path}", file=sys.stderr)
        return

    rows = []
    with manifest_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("split") == "test":
                rows.append(row)

    print(f"Evaluating baseline detector on {len(rows)} held-out test samples...")
    detector = get_detector()

    y_true = []
    y_score = []
    errors = 0

    for row in rows:
        img_path = Path("datasets") / row["relative_path"]
        label = row["label"]
        true_label = 1 if label == "ai_generated" else 0

        if not img_path.is_file():
            print(f"File not found: {img_path}")
            errors += 1
            continue

        try:
            with Image.open(img_path) as img:
                rgb = img.convert("RGB")
                output = detector.infer(rgb)
                if output.fake_probability is not None:
                    y_true.append(true_label)
                    y_score.append(output.fake_probability)
                else:
                    errors += 1
        except Exception as exc:
            print(f"Inference error on {img_path}: {exc}")
            errors += 1

    if not y_true:
        print("No valid test predictions generated.")
        return

    threshold = 0.5
    y_pred = [1 if s >= threshold else 0 for s in y_score]
    acc = float(accuracy_score(y_true, y_pred))
    prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist()
    try:
        auc = float(roc_auc_score(y_true, y_score)) if len(np.unique(y_true)) > 1 else None
    except Exception:
        auc = None

    print("\nHeld-Out Test Evaluation Results (Threshold 0.5):")
    print(f"  Test Samples Evaluated: {len(y_true)} (Errors: {errors})")
    print(f"  Accuracy:  {acc:.4f}")
    print(f"  Precision: {prec:.4f}")
    print(f"  Recall:    {rec:.4f}")
    print(f"  F1 Score:  {f1:.4f}")
    print(f"  ROC AUC:   {auc if auc is not None else 'N/A'}")
    print(f"  Confusion Matrix: {cm}")


if __name__ == "__main__":
    import sys
    main()
