"""Group-aware evaluation and fold-level variation analysis for dataset shortcut auditing."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
from sklearn.model_selection import StratifiedKFold, LeaveOneGroupOut
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score


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
    groups = []

    for row in rows:
        img_path = Path("datasets") / row["relative_path"]
        label = 1 if row["label"] == "ai_generated" else 0
        group = row["generator_family"]  # e.g. imagenet, docci, z-image-turbo, etc.

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
        groups.append(group)

    X_arr = np.array(X, dtype=np.float32)
    y_arr = np.array(y, dtype=np.int32)
    groups_arr = np.array(groups)

    print(f"Total samples loaded: {len(y_arr)}")

    # E3.1: Reproduce stratified 5-fold CV with fold-level breakdown
    print("\n=== E3.1 Stratified 5-Fold CV Fold-Level Scores ===")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    for fold, (train_idx, test_idx) in enumerate(skf.split(X_arr, y_arr), 1):
        X_tr, X_te = X_arr[train_idx], X_arr[test_idx]
        y_tr, y_te = y_arr[train_idx], y_arr[test_idx]

        lr = LogisticRegression(max_iter=1000, random_state=42)
        lr.fit(X_tr, y_tr)
        lr_acc = accuracy_score(y_te, lr.predict(X_te))

        dt = DecisionTreeClassifier(max_depth=4, random_state=42)
        dt.fit(X_tr, y_tr)
        dt_acc = accuracy_score(y_te, dt.predict(X_te))

        print(f"  Fold {fold}: LR Accuracy = {lr_acc:.4f} | DT Accuracy = {dt_acc:.4f} (test size: {len(test_idx)})")

    # E3.2: Group-aware evaluation grouped by major source groups
    print("\n=== E3.2 Group-Aware Evaluation (Grouped by generator_family / source) ===")
    # Group real sources vs AI generator families
    unique_groups = set(groups_arr)
    print(f"Unique source/generator groups: {sorted(list(unique_groups))}")

    # Leave-One-Group-Out cross-validation is robust if groups are sufficiently large.
    # Here many groups have n=1, so logo.split might fail or be trivial. Let's inspect group counts.
    group_counts = Counter(groups_arr)
    print("Group counts:", dict(group_counts.most_common()))


if __name__ == "__main__":
    main()
