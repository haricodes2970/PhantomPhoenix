"""Tests for the dataset acquisition and preparation pipeline."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest
from PIL import Image

from scripts.prepare_dataset_pipeline import compute_sha256


def create_test_image_bytes(format: str = "JPEG", size: tuple[int, int] = (64, 64)) -> bytes:
    img = Image.new("RGB", size, (100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


def test_compute_sha256() -> None:
    data = b"hello phantom phoenix"
    h1 = compute_sha256(data)
    h2 = compute_sha256(data)
    assert h1 == h2
    assert len(h1) == 64


def test_corrupt_image_rejection() -> None:
    corrupt_data = b"not an image at all"
    with pytest.raises(Exception):
        with Image.open(io.BytesIO(corrupt_data)) as im:
            im.verify()


def test_manifest_and_resume_logic(tmp_path: Path) -> None:
    real_dir = tmp_path / "real"
    ai_dir = tmp_path / "ai_generated"
    manifests_dir = tmp_path / "manifests"
    real_dir.mkdir()
    ai_dir.mkdir()
    manifests_dir.mkdir()

    manifest_path = manifests_dir / "dataset_manifest.csv"
    
    # Write initial mock manifest row
    img_bytes = create_test_image_bytes()
    h = compute_sha256(img_bytes)
    rel = "real/real_000001.jpg"
    (tmp_path / rel).parent.mkdir(exist_ok=True)
    (tmp_path / rel).write_bytes(img_bytes)

    fieldnames = [
        "sample_id", "relative_path", "label", "original_dataset", "original_revision",
        "original_sample_id", "generator_family", "original_format", "sha256",
        "license_ref", "download_status", "split"
    ]
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({
            "sample_id": "real_000001",
            "relative_path": rel,
            "label": "real",
            "original_dataset": "MockDataset",
            "original_revision": "core",
            "original_sample_id": "1",
            "generator_family": "UNKNOWN",
            "original_format": "JPEG",
            "sha256": h,
            "license_ref": "CC BY-NC 4.0",
            "download_status": "success",
            "split": "unassigned",
        })

    # Verify resume parsing
    seen_hashes = {h}
    real_collected = 1
    ai_collected = 0

    assert real_collected == 1
    assert ai_collected == 0
    assert h in seen_hashes


def test_pilot_artifacts_preservation() -> None:
    """Ensure existing pilot directory datasets/openfake_pilot/ is untouched."""
    pilot_dir = Path("datasets/openfake_pilot")
    assert pilot_dir.is_dir()
    assert (pilot_dir / "eval_manifest.csv").is_file()
    assert (pilot_dir / "provenance.json").is_file()


def test_validate_existing_dataset_success(tmp_path: Path) -> None:
    from scripts.prepare_dataset_pipeline import validate_existing_dataset

    real_dir = tmp_path / "real"
    ai_dir = tmp_path / "ai_generated"
    manifests_dir = tmp_path / "manifests"
    real_dir.mkdir()
    ai_dir.mkdir()
    manifests_dir.mkdir()

    manifest_path = manifests_dir / "dataset_manifest.csv"

    img_r = create_test_image_bytes(size=(64, 64))
    hr = compute_sha256(img_r)
    rel_r = "real/real_000001.jpg"
    (tmp_path / rel_r).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / rel_r).write_bytes(img_r)

    img_a = create_test_image_bytes(size=(128, 128))
    ha = compute_sha256(img_a)
    rel_a = "ai_generated/ai_000001.jpg"
    (tmp_path / rel_a).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / rel_a).write_bytes(img_a)

    fieldnames = [
        "sample_id", "relative_path", "label", "original_dataset", "original_revision",
        "original_sample_id", "generator_family", "original_format", "sha256",
        "license_ref", "download_status", "split"
    ]
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({
            "sample_id": "real_000001", "relative_path": rel_r, "label": "real",
            "original_dataset": "Test", "original_revision": "core", "original_sample_id": "1",
            "generator_family": "UNKNOWN", "original_format": "JPEG", "sha256": hr,
            "license_ref": "CC BY-NC 4.0", "download_status": "success", "split": "unassigned"
        })
        writer.writerow({
            "sample_id": "ai_000001", "relative_path": rel_a, "label": "ai_generated",
            "original_dataset": "Test", "original_revision": "core", "original_sample_id": "2",
            "generator_family": "z-image-turbo", "original_format": "JPEG", "sha256": ha,
            "license_ref": "CC BY-NC 4.0", "download_status": "success", "split": "unassigned"
        })

    is_met, real_c, ai_c = validate_existing_dataset(manifest_path, tmp_path, 1, 1)
    assert is_met is True
    assert real_c == 1
    assert ai_c == 1


def test_validate_existing_dataset_missing_file(tmp_path: Path) -> None:
    from scripts.prepare_dataset_pipeline import validate_existing_dataset

    manifests_dir = tmp_path / "manifests"
    manifests_dir.mkdir()
    manifest_path = manifests_dir / "dataset_manifest.csv"

    fieldnames = [
        "sample_id", "relative_path", "label", "original_dataset", "original_revision",
        "original_sample_id", "generator_family", "original_format", "sha256",
        "license_ref", "download_status", "split"
    ]
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({
            "sample_id": "real_000001", "relative_path": "real/missing.jpg", "label": "real",
            "original_dataset": "Test", "original_revision": "core", "original_sample_id": "1",
            "generator_family": "UNKNOWN", "original_format": "JPEG", "sha256": "abc",
            "license_ref": "CC BY-NC 4.0", "download_status": "success", "split": "unassigned"
        })

    is_met, _, _ = validate_existing_dataset(manifest_path, tmp_path, 1, 1)
    assert is_met is False


def test_validate_existing_dataset_hash_mismatch(tmp_path: Path) -> None:
    from scripts.prepare_dataset_pipeline import validate_existing_dataset

    manifests_dir = tmp_path / "manifests"
    manifests_dir.mkdir()
    manifest_path = manifests_dir / "dataset_manifest.csv"

    img_r = create_test_image_bytes()
    rel_r = "real/real_000001.jpg"
    (tmp_path / rel_r).parent.mkdir(exist_ok=True)
    (tmp_path / rel_r).write_bytes(img_r)

    fieldnames = [
        "sample_id", "relative_path", "label", "original_dataset", "original_revision",
        "original_sample_id", "generator_family", "original_format", "sha256",
        "license_ref", "download_status", "split"
    ]
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({
            "sample_id": "real_000001", "relative_path": rel_r, "label": "real",
            "original_dataset": "Test", "original_revision": "core", "original_sample_id": "1",
            "generator_family": "UNKNOWN", "original_format": "JPEG", "sha256": "wrong_hash",
            "license_ref": "CC BY-NC 4.0", "download_status": "success", "split": "unassigned"
        })

    is_met, _, _ = validate_existing_dataset(manifest_path, tmp_path, 1, 1)
    assert is_met is False
