"""Detector evaluation harness for benchmark datasets and manifest evaluation."""

from __future__ import annotations

import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score, confusion_matrix

from backend.config import settings
from backend.detector import DetectorAdapter, get_detector


class DetectorEvaluator:
    """Harness to evaluate the AI image detector against a labeled manifest."""

    def __init__(self, detector: DetectorAdapter | None = None) -> None:
        self.detector = detector or get_detector()

    def evaluate_manifest(
        self,
        manifest_path: str | Path,
        threshold: float = 0.5,
        device: str = "auto",
    ) -> dict[str, Any]:
        """
        Evaluate detector on a CSV or JSON manifest.

        Manifest format (CSV):
            path,label
            /path/to/real1.jpg,real
            /path/to/fake1.jpg,fake
        or JSON:
            [{"path": "...", "label": "real"}, ...]
        """
        manifest_file = Path(manifest_path)
        if not manifest_file.is_file():
            raise FileNotFoundError(f"Manifest not found: {manifest_file}")

        entries: list[dict[str, str]] = []
        if manifest_file.suffix.lower() == ".json":
            with manifest_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    entries.append({"path": str(item.get("path", "")), "label": str(item.get("label", ""))})
        else:
            with manifest_file.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    entries.append({"path": row.get("path", ""), "label": row.get("label", "")})

        y_true: list[int] = []
        y_score: list[float] = []
        exclusions: list[dict[str, str]] = []
        inference_errors: list[dict[str, str]] = []

        start_time = time.perf_counter()
        processed_count = 0

        for entry in entries:
            img_path = Path(entry["path"])
            label_str = entry["label"].strip().lower()

            # Normalize label to binary (0 = real, 1 = fake/ai)
            if label_str in ("real", "authentic", "0"):
                true_label = 0
            elif label_str in ("fake", "ai", "synthetic", "1"):
                true_label = 1
            else:
                exclusions.append({"path": str(img_path), "reason": f"Invalid label: {entry['label']}"})
                continue

            if not img_path.is_file():
                exclusions.append({"path": str(img_path), "reason": "File not found"})
                continue

            try:
                with Image.open(img_path) as img:
                    img = img.convert("RGB")
                    output = self.detector.infer(img)
                    if output.fake_probability is None:
                        inference_errors.append({"path": str(img_path), "reason": "Model produced null probability"})
                        continue
                    y_true.append(true_label)
                    y_score.append(output.fake_probability)
                    processed_count += 1
            except Exception as exc:
                inference_errors.append({"path": str(img_path), "reason": str(exc)})

        elapsed = time.perf_counter() - start_time

        # Compute metrics if we have valid samples
        metrics: dict[str, Any] = {}
        if len(y_true) > 0:
            y_pred = [1 if s >= threshold else 0 for s in y_score]
            acc = float(accuracy_score(y_true, y_pred))
            prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
            cm = confusion_matrix(y_true, y_pred).tolist()

            try:
                auc = float(roc_auc_score(y_true, y_score))
            except Exception:
                auc = None

            metrics = {
                "accuracy": round(acc, 4),
                "precision": round(float(prec), 4),
                "recall": round(float(rec), 4),
                "f1_score": round(float(f1), 4),
                "roc_auc": round(auc, 4) if auc is not None else None,
                "confusion_matrix": cm,  # [[TN, FP], [FN, TP]]
            }

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model_id": settings.model_id,
            "decision_threshold": threshold,
            "total_entries": len(entries),
            "processed_samples": processed_count,
            "excluded_count": len(exclusions),
            "inference_error_count": len(inference_errors),
            "duration_seconds": round(elapsed, 4),
            "metrics": metrics,
            "exclusions": exclusions,
            "inference_errors": inference_errors,
        }

        return report

    def export_summary(self, report: dict[str, Any], output_dir: str | Path) -> tuple[Path, Path]:
        """Export evaluation report as JSON and Markdown summary."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        json_file = out_path / "evaluation_report.json"
        md_file = out_path / "evaluation_summary.md"

        with json_file.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        m = report["metrics"]
        md_content = f"""# Phantom Phoenix Detector Evaluation Summary

- **Timestamp:** {report["timestamp"]}
- **Model ID:** `{report["model_id"]}`
- **Decision Threshold:** {report["decision_threshold"]}
- **Total Manifest Entries:** {report["total_entries"]}
- **Processed Samples:** {report["processed_samples"]}
- **Exclusions / Errors:** {report["excluded_count"]} / {report["inference_error_count"]}
- **Duration:** {report["duration_seconds"]}s

## Aggregate Performance Metrics
- **Accuracy:** {m.get("accuracy", "N/A")}
- **Precision:** {m.get("precision", "N/A")}
- **Recall:** {m.get("recall", "N/A")}
- **F1 Score:** {m.get("f1_score", "N/A")}
- **ROC AUC:** {m.get("roc_auc", "N/A")}

## Confusion Matrix
```
{m.get("confusion_matrix", [])}
```

*Note: Evaluation results reflect the test set evaluated. Performance on out-of-distribution or state-of-the-art commercial generators may vary.*
"""
        with md_file.open("w", encoding="utf-8") as f:
            f.write(md_content)

        return json_file, md_file