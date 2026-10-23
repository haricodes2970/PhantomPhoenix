"""Format-only diagnostic classifier to test for dataset-source confounding."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import numpy as np
from PIL import Image
from sklearn.model_selection import StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, roc_auc_score


def main() -> None:
    manifest_path = Path("datasets/manifests/dataset_manifest.csv")
    if not manifest_path.is_file():
        print("Manifest not found.")
        return

    rows = []
    with manifest_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    X = []
    y = []

    for row in rows:
        img_path = Path("datasets") / row["relative_path"]
        label = 1 if row["label"] == "ai_generated" else 0

        if not img_path.is_file():
            continue

        size_bytes = img_path.stat().st_size
        try:
            with Image.open(img_path) as img:
                w, h = img.size
                ar = w / h if h > 0 else 0.0
                fmt_jpeg = 1.0 if img.format == "JPEG" else 0.0
                fmt_png = 1.0 if img.format == "PNG" else 0.0
        except Exception:
            w, h, ar, fmt_jpeg, fmt_png = 0, 0, 0.0, 0.0, 0.0

        # Features: width, height, aspect_ratio, log(file_size), format flags
        features = [
            float(w),
            float(h),
            float(ar),
            float(np.log(size_bytes + 1)),
            fmt_jpeg,
            fmt_png,
        ]
        X.append(features)
        y.append(label)

    X_arr = np.array(X, dtype=np.float32)
    y_arr = np.array(y, dtype=np.int32)

    print(f"Dataset samples for format diagnostic: {len(y_arr)} (Real: {sum(y_arr == 0)}, AI: {sum(y_arr == 1)})")

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    lr_accs = []
    dt_accs = []

    for train_idx, test_idx in skf.split(X_arr, y_arr):
        X_train, X_test = X_arr[train_idx], X_arr[test_idx]
        y_train, y_test = y_arr[train_idx], y_arr[test_idx]

        # Logistic Regression
        lr = LogisticRegression(max_iter=1000, random_state=42)
        lr.fit(X_train, y_train)
        lr_preds = lr.predict(X_test)
        lr_accs.append(accuracy_score(y_test, lr_preds))

        # Decision Tree
        dt = DecisionTreeClassifier(max_depth=4, random_state=42)
        dt.fit(X_train, y_train)
        dt_preds = dt.predict(X_test)
        dt_accs.append(accuracy_score(y_test, dt_preds))

    print(f"Format-Only Logistic Regression 5-fold CV Accuracy: {np.mean(lr_accs):.4f} (+/- {np.std(lr_accs):.4f})")
    print(f"Format-Only Decision Tree 5-fold CV Accuracy: {np.mean(dt_accs):.4f} (+/- {np.std(dt_accs):.4f})")
    print("Interpretation: If accuracy is close to 0.50 (chance), format properties do not confound the task. If significantly higher, source-specific file size/dimension artifacts may contribute.")


if __name__ == "__main__":
    main()
