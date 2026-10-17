"""Generator-family generalization and confidence interval audit script."""

from __future__ import annotations

import csv
import json
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np


def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
    if total == 0:
        return (0.0, 0.0)
    # z for 95% confidence is ~1.96
    z = 1.96 if confidence == 0.95 else 1.96
    p = successes / total
    denominator = 1 + z**2 / total
    centre_adjusted_probability = p + z**2 / (2 * total)
    adjusted_standard_deviation = z * np.sqrt((p * (1 - p) + z**2 / (4 * total)) / total)
    lower_bound = (centre_adjusted_probability - adjusted_standard_deviation) / denominator
    upper_bound = (centre_adjusted_probability + adjusted_standard_deviation) / denominator
    return (float(max(0.0, lower_bound)), float(min(1.0, upper_bound)))


def main() -> None:
    manifest_path = Path("datasets/manifests/dataset_manifest.csv")
    preds_path = Path("datasets/manifests/experiment_baseline_eval/per_sample_predictions.json")

    if not manifest_path.is_file() or not preds_path.is_file():
        print("Manifest or predictions not found.")
        return

    rows = []
    with manifest_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    predictions = json.loads(preds_path.read_text(encoding="utf-8"))

    # Inspect splits by generator family
    split_family = defaultdict(Counter)
    for row in rows:
        sp = row.get("split", "unassigned")
        gen = row.get("generator_family", "unknown")
        split_family[sp][gen] += 1

    print("=== Generator Family Distribution Across Splits ===")
    all_gens = sorted(list(set(row["generator_family"] for row in rows)))
    print(f"{'Generator / Source':<20} | {'Train':<6} | {'Val':<6} | {'Test':<6} | {'Total':<6}")
    print("-" * 60)
    for gen in all_gens:
        tr = split_family["train"][gen]
        va = split_family["val"][gen]
        te = split_family["test"][gen]
        tot = tr + va + te
        print(f"{gen:<20} | {tr:<6} | {va:<6} | {te:<6} | {tot:<6}")

    # Per-family test performance at threshold 0.20 and 0.50
    print("\n=== Per-Family Test Performance (n=922) ===")
    fam_stats = defaultdict(lambda: {"total": 0, "tp_50": 0, "fn_50": 0, "tp_20": 0, "fn_20": 0, "real": 0, "tn": 0, "fp": 0})

    for p in predictions:
        gen = p["generator_family"]
        true_l = p["true_label"]
        score = p["fake_probability"]

        pred_50 = 1 if score >= 0.50 else 0
        pred_20 = 1 if score >= 0.20 else 0

        if true_l == 1:
            fam_stats[gen]["total"] += 1
            if pred_50 == 1:
                fam_stats[gen]["tp_50"] += 1
            else:
                fam_stats[gen]["fn_50"] += 1
            if pred_20 == 1:
                fam_stats[gen]["tp_20"] += 1
            else:
                fam_stats[gen]["fn_20"] += 1
        else:
            fam_stats[gen]["real"] += 1
            if pred_50 == 0:
                fam_stats[gen]["tn"] += 1
            else:
                fam_stats[gen]["fp"] += 1

    print(f"{'Family / Source':<18} | {'N':<4} | {'Recall@0.50':<11} | {'Recall@0.20':<11} | {'95% CI @0.20 (Wilson)'}")
    print("-" * 70)
    for gen, st in sorted(fam_stats.items(), key=lambda x: x[1]["total"], reverse=True):
        tot = st["total"]
        if tot > 0:
            rec_50 = st["tp_50"] / tot
            rec_20 = st["tp_20"] / tot
            ci_low, ci_high = wilson_score_interval(st["tp_20"], tot)
            print(f"{gen:<18} | {tot:<4} | {rec_50:<11.4f} | {rec_20:<11.4f} | [{ci_low:.4f}, {ci_high:.4f}]")
        else:
            print(f"{gen:<18} | Real source (TN={st['tn']}, FP={st['fp']})")

    # Overall test metrics and confidence intervals
    y_true = np.array([p["true_label"] for p in predictions])
    y_score = np.array([p["fake_probability"] for p in predictions])

    for thresh, name in [(0.50, "Baseline (0.50)"), (0.20, "Candidate (0.20)")]:
        preds = np.array([1 if s >= thresh else 0 for s in y_score])
        correct = (preds == y_true)
        acc_succ = int(correct.sum())
        acc_tot = len(y_true)
        acc_ci = wilson_score_interval(acc_succ, acc_tot)

        ai_mask = (y_true == 1)
        ai_succ = int(preds[ai_mask].sum())
        ai_tot = int(ai_mask.sum())
        rec_ci = wilson_score_interval(ai_succ, ai_tot)

        print(f"\n{name} Confidence Intervals (n=922):")
        print(f"  Accuracy: {acc_succ/acc_tot:.4f} (95% Wilson CI: [{acc_ci[0]:.4f}, {acc_ci[1]:.4f}])")
        print(f"  AI Recall: {ai_succ/ai_tot:.4f} (95% Wilson CI: [{rec_ci[0]:.4f}, {rec_ci[1]:.4f}])")

    out_dir = Path("datasets/manifests/experiment_generalization_eval")
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "generalization_audit.json"
    summary_path.write_text(json.dumps({
        "per_family_stats": {k: dict(v) for k, v in fam_stats.items()}
    }, indent=2), encoding="utf-8")
    print(f"\nGeneralization audit saved to {summary_path}")


if __name__ == "__main__":
    main()
