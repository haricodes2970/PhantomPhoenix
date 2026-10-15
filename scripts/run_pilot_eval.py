"""Run the DetectorEvaluator against an evaluation manifest."""

from __future__ import annotations

import sys
from backend.evaluation import DetectorEvaluator


def main() -> None:
    manifest_path = sys.argv[1] if len(sys.argv) > 1 else "datasets/openfake_pilot/eval_manifest_small.csv"
    output_dir = "datasets/openfake_pilot/results"

    print(f"Running evaluation on manifest: {manifest_path}...")
    evaluator = DetectorEvaluator()
    report = evaluator.evaluate_manifest(manifest_path, threshold=0.5)

    json_out, md_out = evaluator.export_summary(report, output_dir)
    print(f"\nEvaluation complete!")
    print(f"JSON Report: {json_out}")
    print(f"Markdown Summary: {md_out}")

    metrics = report["metrics"]
    print(f"\nResults:")
    print(f"  Processed Samples: {report['processed_samples']}")
    print(f"  Accuracy:  {metrics.get('accuracy')}")
    print(f"  Precision: {metrics.get('precision')}")
    print(f"  Recall:    {metrics.get('recall')}")
    print(f"  F1 Score:  {metrics.get('f1_score')}")
    print(f"  ROC AUC:   {metrics.get('roc_auc')}")
    print(f"  Confusion Matrix: {metrics.get('confusion_matrix')}")


if __name__ == "__main__":
    main()
