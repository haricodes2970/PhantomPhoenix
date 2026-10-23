#!/usr/bin/env python3
"""Analyze PHANTOM PHOENIX's saved OpenFake pilot predictions.

Uses only the Python standard library. It does not run model inference, change
production thresholds, or modify production code.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def get_label(sample: dict[str, Any]) -> int:
    if sample.get("true_label") in (0, 1):
        return int(sample["true_label"])
    label = str(sample.get("label", "")).strip().lower()
    if label in {"fake", "ai", "ai_generated", "generated"}:
        return 1
    if label in {"real", "authentic"}:
        return 0
    raise ValueError(f"Cannot determine true label for sample: {sample.get('path')}")


def confusion(labels: list[int], scores: list[float], threshold: float) -> dict[str, int]:
    predicted = [int(score >= threshold) for score in scores]
    return {
        "tp": sum(y == 1 and p == 1 for y, p in zip(labels, predicted)),
        "tn": sum(y == 0 and p == 0 for y, p in zip(labels, predicted)),
        "fp": sum(y == 0 and p == 1 for y, p in zip(labels, predicted)),
        "fn": sum(y == 1 and p == 0 for y, p in zip(labels, predicted)),
    }


def metrics(labels: list[int], scores: list[float], threshold: float) -> dict[str, float | int]:
    c = confusion(labels, scores, threshold)
    tp, tn, fp, fn = c["tp"], c["tn"], c["fp"], c["fn"]
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        **c,
        "accuracy": (tp + tn) / len(labels) if labels else 0.0,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def roc_auc(labels: list[int], scores: list[float]) -> float | None:
    positives = [score for label, score in zip(labels, scores) if label == 1]
    negatives = [score for label, score in zip(labels, scores) if label == 0]
    if not positives or not negatives:
        return None
    # Mann–Whitney formulation; ties receive half credit.
    wins = 0.0
    for positive in positives:
        for negative in negatives:
            if positive > negative:
                wins += 1.0
            elif positive == negative:
                wins += 0.5
    return wins / (len(positives) * len(negatives))


def pct(value: float) -> str:
    return f"{value:.4f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions", type=Path, help="per_sample_predictions.json")
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional official evaluation_report.json to cross-check aggregate metrics",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Threshold used for the primary recomputed metrics (default: 0.5)",
    )
    parser.add_argument(
        "--low-sample",
        type=int,
        default=2,
        help="Warn about generator groups with this many or fewer samples (default: 2)",
    )
    args = parser.parse_args()

    payload = load_json(args.predictions)
    raw_samples = payload.get("samples")
    if not isinstance(raw_samples, list) or not raw_samples:
        raise ValueError("Input must contain a non-empty 'samples' list")

    samples: list[dict[str, Any]] = []
    labels: list[int] = []
    scores: list[float] = []
    for sample in raw_samples:
        if not isinstance(sample, dict):
            raise ValueError("Every entry in 'samples' must be an object")
        if sample.get("status", "ok") != "ok" or sample.get("error"):
            print(f"WARNING: non-success sample included in file: {sample.get('path')}")
        score = float(sample["fake_probability"])
        if not math.isfinite(score) or not 0.0 <= score <= 1.0:
            raise ValueError(f"Invalid fake_probability for {sample.get('path')}: {score}")
        label = get_label(sample)
        samples.append(sample)
        labels.append(label)
        scores.append(score)

    n_real = sum(label == 0 for label in labels)
    n_fake = sum(label == 1 for label in labels)
    primary = metrics(labels, scores, args.threshold)
    auc = roc_auc(labels, scores)

    print("PHANTOM PHOENIX — PILOT PREDICTION ANALYSIS")
    print(f"Input: {args.predictions}")
    print(f"Samples: {len(samples)} | real={n_real} | fake={n_fake}")
    print(f"Primary threshold: {args.threshold:.2f}")
    print(
        "Confusion matrix [[TN, FP], [FN, TP]]: "
        f"[[{primary['tn']}, {primary['fp']}], [{primary['fn']}, {primary['tp']}]]"
    )
    print(
        f"Accuracy={primary['accuracy']:.4f}  Precision(fake)={primary['precision']:.4f}  "
        f"Recall(fake)={primary['recall']:.4f}  F1={primary['f1']:.4f}  "
        f"ROC-AUC={auc if auc is not None else 'undefined'}"
    )

    if args.report:
        official = load_json(args.report)
        reported = official.get("metrics", {})
        print("\nOfficial aggregate report cross-check:")
        print(
            f"processed={official.get('processed_samples')} "
            f"excluded={official.get('excluded_count')} "
            f"inference_errors={official.get('inference_error_count')} "
            f"reported_threshold={official.get('decision_threshold')}"
        )
        calculated_cm = [
            [primary["tn"], primary["fp"]],
            [primary["fn"], primary["tp"]],
        ]
        checks = {
            "accuracy": primary["accuracy"],
            "precision": primary["precision"],
            "recall": primary["recall"],
            "f1_score": primary["f1"],
            "roc_auc": auc,
        }
        all_match = True
        for key, value in checks.items():
            expected = reported.get(key)
            match = (
                value is not None
                and expected is not None
                and math.isclose(float(value), float(expected), rel_tol=0, abs_tol=0.00011)
            )
            all_match &= match
            print(f"  {key}: recomputed={value} reported={expected} match={match}")
        cm_match = calculated_cm == reported.get("confusion_matrix")
        all_match &= cm_match
        print(f"  confusion_matrix: recomputed={calculated_cm} reported={reported.get('confusion_matrix')} match={cm_match}")
        if not all_match:
            print(
                "WARNING: per-sample file and official aggregate do not fully match. "
                "Do not combine their results without investigating the inference-pass difference."
            )

    print("\nThreshold sweep (score >= threshold means predicted fake):")
    print("threshold  TP  TN  FP  FN  accuracy  precision  recall  F1")
    for step in range(1, 10):
        threshold = step / 10
        row = metrics(labels, scores, threshold)
        print(
            f"{threshold:>9.1f} {row['tp']:>3} {row['tn']:>3} {row['fp']:>3} {row['fn']:>3} "
            f"{row['accuracy']:>9.4f} {row['precision']:>10.4f} "
            f"{row['recall']:>7.4f} {row['f1']:>6.4f}"
        )

    false_negatives = [
        sample for sample, label, score in zip(samples, labels, scores)
        if label == 1 and score < args.threshold
    ]
    false_positives = [
        sample for sample, label, score in zip(samples, labels, scores)
        if label == 0 and score >= args.threshold
    ]
    print(f"\nFalse negatives at threshold {args.threshold:.2f}: {len(false_negatives)}")
    fn_by_family = Counter(str(sample.get("source_model") or "Unknown") for sample in false_negatives)
    for family, count in fn_by_family.most_common():
        print(f"  {family}: {count}")
    if false_negatives:
        highest = max(false_negatives, key=lambda sample: float(sample["fake_probability"]))
        print(
            "Highest-scoring false negative: "
            f"{highest.get('path')} score={float(highest['fake_probability']):.6f} "
            f"family={highest.get('source_model')}"
        )
        below_027 = sum(float(sample["fake_probability"]) < 0.27 for sample in false_negatives)
        print(f"False negatives below 0.27: {below_027}/{len(false_negatives)}")
    print(f"\nFalse positives at threshold {args.threshold:.2f}: {len(false_positives)}")
    for sample in false_positives:
        print(f"  {sample.get('path')} score={float(sample['fake_probability']):.6f}")

    # Per-family recall is computed only for positive (fake) examples.
    family_total: Counter[str] = Counter()
    family_detected: Counter[str] = Counter()
    for sample, label, score in zip(samples, labels, scores):
        if label != 1:
            continue
        family = str(sample.get("source_model") or "Unknown")
        family_total[family] += 1
        if score >= args.threshold:
            family_detected[family] += 1

    print("\nPer-generator recall on fake samples:")
    for family, total in sorted(family_total.items(), key=lambda item: (-item[1], item[0].lower())):
        detected = family_detected[family]
        warning = f"  WARNING: n<={args.low_sample}; too few samples for a stable family-level claim" if total <= args.low_sample else ""
        print(f"  {family}: n={total}, detected={detected}, recall={detected / total:.3f}{warning}")

    print(
        "\nInterpretation guardrails:\n"
        "- ROC-AUC measures score ranking across thresholds; recall measures detection at one threshold.\n"
        "- A high AUC can coexist with low recall at 0.5. This pilot alone cannot distinguish calibration drift, "
        "generator coverage gaps, and sample-size effects. Treat these as hypotheses.\n"
        "- This is a small pilot, not a generalization claim. Do not promote a threshold from this set alone.\n"
        "- This script analyzes saved predictions only; it does not perform inference or modify production code."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
