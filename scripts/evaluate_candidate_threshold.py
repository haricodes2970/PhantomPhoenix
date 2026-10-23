"""Evaluate candidate thresholds on the locked test set (922 samples) using saved predictions."""

from __future__ import annotations

import csv
import json
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, roc_auc_score, average_precision_score


def main() -> None:
    preds_path = Path("datasets/manifests/experiment_baseline_eval/per_sample_predictions.json")
    if not preds_path.is_file():
        print(f"Predictions not found: {preds_path}. Run baseline evaluation first.")
        return

    predictions = json.loads(preds_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(predictions)} sample predictions.")

    y_true = np.array([p["true_label"] for p in predictions])
    y_score = np.array([p["fake_probability"] for p in predictions])

    # Candidate thresholds to evaluate on test set: 0.50 (baseline), 0.20 (conservative val-tuned), 0.05 (F1-optimal val-tuned)
    candidate_thresholds = [0.50, 0.20, 0.05]
    results = {}

    for t in candidate_thresholds:
        pred_arr = np.array([1 if s >= t else 0 for s in y_score])
        acc = float(accuracy_score(y_true, pred_arr))
        prec, rec, f1, _ = precision_recall_fscore_support(y_true, pred_arr, average="binary", zero_division=0)
        cm = confusion_matrix(y_true, pred_arr, labels=[0, 1]).tolist()
        tn, fp, fn, tp = cm[0][0], cm[0][1], cm[1][0], cm[1][1]
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
        auc = float(roc_auc_score(y_true, y_score))
        ap = float(average_precision_score(y_true, y_score))

        results[str(t)] = {
            "threshold": t,
            "accuracy": round(acc, 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "roc_auc": round(auc, 4),
            "pr_auc": round(ap, 4),
            "false_positive_rate": round(fpr, 4),
            "false_negative_rate": round(fnr, 4),
            "confusion_matrix": cm,
        }

        print(f"\nThreshold {t:.2f}:")
        print(f"  Accuracy:  {acc:.4f}")
        print(f"  Precision: {float(prec):.4f}")
        print(f"  Recall:    {float(rec):.4f}")
        print(f"  F1 Score:  {float(f1):.4f}")
        print(f"  FPR:       {fpr:.4f} | FNR: {fnr:.4f}")
        print(f"  Confusion Matrix: {cm}")

    # Per-generator family breakdown at threshold 0.20
    print("\nPer-Generator Family Performance at Candidate Threshold 0.20:")
    gen_stats = defaultdict(lambda: {"total": 0, "tp": 0, "fn": 0, "fp": 0, "tn": 0})
    for p in predictions:
        gen = p["generator_family"]
        true_l = p["true_label"]
        pred_l = 1 if p["fake_probability"] >= 0.20 else 0

        if true_l == 1:
            gen_stats[gen]["total"] += 1
            if pred_l == 1:
                gen_stats[gen]["tp"] += 1
            else:
                gen_stats[gen]["fn"] += 1
        else:
            gen_stats[gen]["total"] += 1
            if pred_l == 0:
                gen_stats[gen]["tn"] += 1
            else:
                gen_stats[gen]["fp"] += 1

    per_family = {}
    for gen, st in sorted(gen_stats.items(), key=lambda x: x[1]["total"], reverse=True):
        tot = st["total"]
        if tot < 5:
            note = "Small group (n < 5)"
        else:
            note = ""
        print(f"  {gen:<18} | n={tot:<3} | TP={st['tp']:<3} | FN={st['fn']:<3} | FP={st['fp']:<3} | TN={st['tn']:<3} | {note}")
        per_family[gen] = {"total": tot, **st, "note": note}

    out_dir = Path("datasets/manifests/experiment_threshold_eval")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "candidate_threshold_evaluation.json"
    out_path.write_text(json.dumps({"thresholds": results, "per_generator_family_at_0.20": per_family}, indent=2), encoding="utf-8")
    print(f"\nCandidate threshold evaluation saved to {out_path}")


if __name__ == "__main__":
    main()
