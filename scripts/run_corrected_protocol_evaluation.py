"""Corrected evaluation protocol script with strict validation/test separation."""

from __future__ import annotations

import csv
import json
import time
import math
from pathlib import Path
import numpy as np
from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    roc_auc_score,
    confusion_matrix,
)

from backend.config import settings
from backend.detector import get_detector


def compute_metrics(y_true: list[int], y_score: list[float], threshold: float) -> dict[str, Any]:
    y_arr = np.array(y_true)
    score_arr = np.array(y_score)
    pred_arr = np.array([1 if s >= threshold else 0 for s in y_score])

    if len(y_arr) == 0:
        return {}

    acc = float(accuracy_score(y_arr, pred_arr))
    prec, rec, f1, _ = precision_recall_fscore_support(y_arr, pred_arr, average="binary", zero_division=0)
    cm = confusion_matrix(y_arr, pred_arr, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    fpr = float(fp / (tn + fp)) if (tn + fp) > 0 else 0.0
    fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0
    balanced_acc = float((rec + specificity) / 2.0)

    # 95% Confidence Interval for Accuracy using normal approximation
    n = len(y_arr)
    se_acc = math.sqrt((acc * (1 - acc)) / n) if n > 0 else 0.0
    ci_acc = [max(0.0, acc - 1.96 * se_acc), min(1.0, acc + 1.96 * se_acc)]

    try:
        auc = float(roc_auc_score(y_arr, score_arr)) if len(np.unique(y_arr)) > 1 else None
    except Exception:
        auc = None

    classified_ai_count = int(pred_arr.sum())
    classified_ai_prop = float(classified_ai_count / n) if n > 0 else 0.0

    return {
        "threshold": threshold,
        "sample_count": n,
        "confusion_matrix": cm.tolist(),
        "true_positives": int(tp),
        "false_positives": int(fp),
        "true_negatives": int(tn),
        "false_negatives": int(fn),
        "accuracy": round(acc, 4),
        "accuracy_ci_95": [round(ci_acc[0], 4), round(ci_acc[1], 4)],
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1_score": round(float(f1), 4),
        "specificity": round(specificity, 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "balanced_accuracy": round(balanced_acc, 4),
        "roc_auc": round(auc, 4) if auc is not None else None,
        "classified_ai_count": classified_ai_count,
        "classified_ai_proportion": round(classified_ai_prop, 4),
    }


def main() -> None:
    manifest_path = Path("datasets/manifests/dataset_manifest.csv")
    if not manifest_path.is_file():
        print(f"Manifest not found: {manifest_path}")
        return

    rows_val = []
    rows_test = []
    with manifest_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("split") == "val":
                rows_val.append(row)
            elif row.get("split") == "test":
                rows_test.append(row)

    print(f"Loaded {len(rows_val)} validation samples and {len(rows_test)} test samples.")

    detector = get_detector()
    candidate_thresholds = [0.50, 0.20, 0.05, 0.80]

    # Step 1: Evaluate inference on Validation split
    print("\n--- Running Validation Split Inference ---")
    val_true = []
    val_score = []
    for row in rows_val:
        img_path = Path("datasets") / row["relative_path"]
        true_label = 1 if row["label"] == "ai_generated" else 0
        if not img_path.is_file():
            continue
        try:
            with Image.open(img_path) as img:
                rgb = img.convert("RGB")
                output = detector.infer(rgb)
            if output.fake_probability is not None:
                val_true.append(true_label)
                val_score.append(output.fake_probability)
        except Exception:
            pass

    val_results = {}
    for th in candidate_thresholds:
        val_results[str(th)] = compute_metrics(val_true, val_score, th)

    # Select best validation threshold based on Balanced Accuracy / F1
    best_th = 0.50
    best_bal_acc = -1.0
    for th_str, metrics in val_results.items():
        if metrics["balanced_accuracy"] > best_bal_acc:
            best_bal_acc = metrics["balanced_accuracy"]
            best_th = float(th_str)

    print(f"Selected Validation Threshold (Frozen Policy): {best_th}")

    # Step 2: Evaluate frozen policy ONCE on untouched Test split
    print("\n--- Running Held-Out Test Split Inference with Frozen Threshold ---")
    test_true = []
    test_score = []
    for row in rows_test:
        img_path = Path("datasets") / row["relative_path"]
        true_label = 1 if row["label"] == "ai_generated" else 0
        if not img_path.is_file():
            continue
        try:
            with Image.open(img_path) as img:
                rgb = img.convert("RGB")
                output = detector.infer(rgb)
            if output.fake_probability is not None:
                test_true.append(true_label)
                test_score.append(output.fake_probability)
        except Exception:
            pass

    test_metrics = compute_metrics(test_true, test_score, best_th)

    # Output directory
    out_dir = Path("datasets/manifests/experiment_corrected_eval")
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_data = {
        "model_id": settings.model_id,
        "validation_sample_count": len(val_true),
        "test_sample_count": len(test_true),
        "validation_threshold_sweep": val_results,
        "selected_validation_threshold": best_th,
        "frozen_test_evaluation": test_metrics,
    }

    summary_path = out_dir / "corrected_evaluation_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print(f"\nEvaluation summary saved to: {summary_path}")
    print(json.dumps(test_metrics, indent=2))


if __name__ == "__main__":
    main()
