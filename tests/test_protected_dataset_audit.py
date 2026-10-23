"""Read-only protection-audit tests using synthetic temporary datasets."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from PIL import Image

from scripts.audit_protected_dataset import (
    REQUIRED_COLUMNS,
    SNAPSHOT_COLUMNS,
    build_snapshot,
    canonical_snapshot_bytes,
    duplicate_errors,
    main,
    safe_dataset_path,
    snapshot_digest,
)


FIELDNAMES = sorted(REQUIRED_COLUMNS)


def image_bytes(path: Path, color: tuple[int, int, int]) -> None:
    image = Image.new("RGB", (12, 10), color)
    image.save(path, format="JPEG")


def write_manifest(root: Path, rows: list[dict[str, str]]) -> Path:
    manifest = root / "manifests" / "dataset_manifest.csv"
    manifest.parent.mkdir(parents=True)
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return manifest


def row(root: Path, sample_id: str, split: str, label: str, filename: str, digest: str) -> dict[str, str]:
    relative = f"{label}/{filename}"
    image_bytes(root / relative, (20, 40, 60))
    return {
        "sample_id": sample_id,
        "relative_path": relative,
        "label": label,
        "original_dataset": "Synthetic",
        "original_revision": "v1",
        "original_sample_id": sample_id,
        "generator_family": "family-a" if label == "ai_generated" else "camera-a",
        "original_format": "JPEG",
        "sha256": digest,
        "license_ref": "TEST",
        "download_status": "success",
        "split": split,
    }


def test_valid_inventory_and_snapshot_preserves_assigned_rows(tmp_path: Path) -> None:
    (tmp_path / "real").mkdir()
    (tmp_path / "ai_generated").mkdir()
    rows = [
        row(tmp_path, "real-1", "train", "real", "real-1.jpg", "a" * 64),
        row(tmp_path, "ai-1", "val", "ai_generated", "ai-1.jpg", "b" * 64),
        row(tmp_path, "real-2", "test", "real", "real-2.jpg", "c" * 64),
        row(tmp_path, "ai-2", "unassigned", "ai_generated", "ai-2.jpg", "d" * 64),
    ]
    manifest = write_manifest(tmp_path, rows)
    snapshot = tmp_path / "snapshot.csv"
    metadata = tmp_path / "snapshot.json"
    report = tmp_path / "report.md"

    result = main([
        "--manifest", str(manifest),
        "--dataset-root", str(tmp_path),
        "--snapshot-csv", str(snapshot),
        "--snapshot-metadata", str(metadata),
        "--report", str(report),
    ])

    assert result == 0
    with snapshot.open(encoding="utf-8", newline="") as handle:
        protected = list(csv.DictReader(handle))
    assert len(protected) == 3
    assert {item["original_split"] for item in protected} == {"train", "val", "test"}
    assert "ai-2" not in {item["sample_id"] for item in protected}
    assert manifest.read_text(encoding="utf-8").count("unassigned") == 1
    report_text = report.read_text(encoding="utf-8")
    assert "Dimensions (top buckets)" in report_text
    assert "Split by generator family" in report_text


def test_missing_columns_fails_without_snapshot(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    manifest.write_text("sample_id,split\na,train\n", encoding="utf-8")
    snapshot = tmp_path / "snapshot.csv"
    result = main([
        "--manifest", str(manifest),
        "--dataset-root", str(tmp_path),
        "--snapshot-csv", str(snapshot),
        "--snapshot-metadata", str(tmp_path / "meta.json"),
        "--report", str(tmp_path / "report.md"),
    ])
    assert result == 1
    assert not snapshot.exists()


def test_duplicate_ids_and_hashes_are_detected() -> None:
    rows = [
        {"sample_id": "same", "sha256": "x", "split": "train"},
        {"sample_id": "same", "sha256": "x", "split": "test"},
    ]
    errors = duplicate_errors(rows, assigned_only=True)
    assert any("duplicate sample_id" in error for error in errors)
    assert any("duplicate sha256" in error for error in errors)
    assert any("cross-split exact-hash conflict" in error for error in errors)


def test_path_containment_rejects_absolute_and_escape(tmp_path: Path) -> None:
    assert safe_dataset_path(tmp_path, "/etc/passwd")[1] == "absolute relative_path"
    assert safe_dataset_path(tmp_path, "../outside.jpg")[1] == "path escapes dataset root"
    safe, error = safe_dataset_path(tmp_path, "real/image.jpg")
    assert error is None
    assert safe == (tmp_path / "real/image.jpg").resolve()


def test_missing_and_corrupt_assigned_images_fail_protection(tmp_path: Path) -> None:
    rows = [{
        "sample_id": "missing",
        "relative_path": "real/missing.jpg",
        "label": "real",
        "original_dataset": "Synthetic",
        "original_revision": "v1",
        "original_sample_id": "missing",
        "generator_family": "camera",
        "original_format": "JPEG",
        "sha256": "a" * 64,
        "license_ref": "TEST",
        "download_status": "success",
        "split": "train",
    }]
    manifest = write_manifest(tmp_path, rows)
    result = main([
        "--manifest", str(manifest),
        "--dataset-root", str(tmp_path),
        "--snapshot-csv", str(tmp_path / "snapshot.csv"),
        "--snapshot-metadata", str(tmp_path / "meta.json"),
        "--report", str(tmp_path / "report.md"),
    ])
    assert result == 1
    assert not (tmp_path / "snapshot.csv").exists()


def test_digest_is_deterministic_and_order_independent() -> None:
    rows = [
        {column: f"{column}-b" for column in SNAPSHOT_COLUMNS},
        {column: f"{column}-a" for column in SNAPSHOT_COLUMNS},
    ]
    assert canonical_snapshot_bytes(rows) == canonical_snapshot_bytes(list(reversed(rows)))
    assert snapshot_digest(rows) == snapshot_digest(list(reversed(rows)))


def test_snapshot_refuses_overwrite(tmp_path: Path) -> None:
    (tmp_path / "real").mkdir()
    rows = [row(tmp_path, "real-1", "train", "real", "real-1.jpg", "a" * 64)]
    manifest = write_manifest(tmp_path, rows)
    snapshot = tmp_path / "snapshot.csv"
    snapshot.write_text("sentinel\n", encoding="utf-8")
    result = main([
        "--manifest", str(manifest),
        "--dataset-root", str(tmp_path),
        "--snapshot-csv", str(snapshot),
        "--snapshot-metadata", str(tmp_path / "meta.json"),
        "--report", str(tmp_path / "report.md"),
    ])
    assert result == 4
    assert snapshot.read_text(encoding="utf-8") == "sentinel\n"


def test_verify_snapshot_detects_manifest_change(tmp_path: Path) -> None:
    (tmp_path / "real").mkdir()
    rows = [row(tmp_path, "real-1", "train", "real", "real-1.jpg", "a" * 64)]
    manifest = write_manifest(tmp_path, rows)
    snapshot = tmp_path / "snapshot.csv"
    metadata = tmp_path / "meta.json"
    report = tmp_path / "report.md"
    assert main([
        "--manifest", str(manifest), "--dataset-root", str(tmp_path),
        "--snapshot-csv", str(snapshot), "--snapshot-metadata", str(metadata),
        "--report", str(report),
    ]) == 0
    with manifest.open("a", encoding="utf-8") as handle:
        handle.write("\n")
    assert main([
        "--manifest", str(manifest), "--dataset-root", str(tmp_path),
        "--snapshot-csv", str(snapshot), "--snapshot-metadata", str(metadata),
        "--report", str(tmp_path / "verify-report.md"), "--verify-snapshot",
    ]) == 3
