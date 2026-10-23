"""Benchmark script for alternative detector (CommunityForensics ViT / OwensLab commfor-model-384 port) on locked test set."""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
import numpy as np
from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
)

from backend.config import settings
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

    print(f"Benchmarking detector on {len(rows)} locked test samples...")
    detector = get_detector()
    threshold = 0.50

    y_true = []
    y_score = []
    predictions = []
    inference_errors = []

    start_time = time.perf_counter()

    for i, row in enumerate(rows):
        img_path = Path("datasets") / row["relative_path"]
        label_str = row["label"]
        true_label = 1 if label_str == "ai_generated" else 0

        if not img_path.is_file():
            inference_errors.append({"sample_id": row["sample_id"], "path": str(img_path), "reason": "File not found"})
            continue

        try:
            t0 = time.perf_counter()
            with Image.open(img_path) as img:
                rgb = img.convert("RGB")
                output = detector.infer(rgb)
            latency = time.perf_counter() - t0

            if output.fake_probability is None:
                inference_errors.append({"sample_id": row["sample_id"], "path": str(img_path), "reason": "Null fake probability"})
                continue

            score = output.fake_probability
            pred = 1 if score >= threshold else 0

            y_true.append(true_label)
            y_score.append(score)

            predictions.append({
                "sample_id": row["sample_id"],
                "path": row["relative_path"],
                "label": label_str,
                "true_label": true_label,
                "generator_family": row["generator_family"],
                "fake_probability": score,
                "predicted_label": pred,
                "correct": pred == true_label,
                "device": output.device,
                "duration_seconds": round(latency, 6),
            })
        except Exception as exc:
            inference_errors.append({"sample_id": row["sample_id"], "path": str(img_path), "reason": str(exc)})

    elapsed = time.perf_counter() - start_time

    y_arr = np.array(y_true)
    score_arr = np.array(y_score)
    pred_arr = np.array([1 if s >= threshold else 0 for s in y_score])

    acc = float(accuracy_score(y_arr, pred_arr))
    prec, rec, f1, _ = precision_recall_fscore_support(y_arr, pred_arr, average="binary", zero_division=0)
    cm = confusion_matrix(y_arr, pred_arr, labels=[0, 1]).tolist()
    tn, fp, fn, tp = cm[0][0], cm[0][1], cm[1][0], cm[1][1]
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    try:
        auc = float(roc_auc_score(y_arr, score_arr)) if len(np.unique(y_arr)) > 1 else None
    except Exception:
        auc = None

    try:
        ap = float(average_precision_score(y_arr, score_arr)) if len(np.unique(y_arr)) > 1 else None
    except Exception:
        ap = None

    metrics_summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_id": settings.model_id,
        "model_revision": settings.model_revision,
        "decision_threshold": threshold,
        "total_test_samples": len(rows),
        "evaluated_samples": len(y_true),
        "inference_errors_count": len(inference_errors),
        "total_duration_seconds": round(elapsed, 4),
        "metrics": {
            "accuracy": round(acc, 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "roc_auc": round(auc, 4) if auc is not None else None,
            "pr_auc": round(ap, 4) if ap is not None else None,
            "false_positive_rate": round(fpr, 4),
            "false_negative_rate": round(fnr, 4),
            "confusion_matrix": cm,
        },
        "inference_errors": inference_errors,
    }

    out_dir = Path("datasets/manifests/experiment_alternative_benchmark")
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "evaluation_summary.json"
    preds_path = out_dir / "per_sample_predictions.json"

    summary_path.write_text(json.dumps(metrics_summary, indent=2), encoding="utf-8")
    preds_path.write_text(json.dumps(predictions, indent=2), encoding="utf-8")

    print("\n=== Alternative Detector Benchmark Complete ===")
    print(f"Summary saved to: {summary_path}")
    print(f"Predictions saved to: {preds_path}")
    print(f"Evaluated Samples: {len(y_true)} / {len(rows)}")
    print(f"Accuracy:  {acc:.4f}")
    print(f"Precision: {float(prec):.4f}")
    print(f"Recall:    {float(rec):.4f}")
    print(f"F1 Score:  {float(f1):.4f}")
    print(f"ROC AUC:   {auc if auc is not None else 'N/A'}")
    print(f"PR AUC:    {ap if ap is not None else 'N/A'}")


if __name__ == "__main__":
    main()
