"""Tests for dependency-free near-duplicate candidate audit."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from PIL import Image, ImageEnhance

from scripts.audit_near_duplicates import (
    ALGORITHM, BKTree, dhash64, hamming_distance, main,
)


def make_image(path: Path, color: tuple[int, int, int], size: tuple[int, int] = (64, 64)) -> None:
    Image.new("RGB", size, color).save(path, format="JPEG")


def manifest(root: Path, rows: list[dict[str, str]]) -> Path:
    path = root / "dataset_manifest.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        fields = list(rows[0])
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    return path


def row(sample_id: str, relative_path: str, sha: str, split: str) -> dict[str, str]:
    return {
        "sample_id": sample_id, "sha256": sha, "relative_path": relative_path,
        "label": "real", "split": split, "generator_family": "camera",
    }


def test_hamming_distance_and_bktree_threshold() -> None:
    tree = BKTree()
    from scripts.audit_near_duplicates import Sample
    first = Sample("a", "a" * 64, "a.jpg", "real", "train", "camera")
    second = Sample("b", "b" * 64, "b.jpg", "real", "test", "camera")
    tree.add(0, first)
    tree.add(3, second)
    assert hamming_distance(0, 3) == 2
    assert [s.sample_id for _, s in tree.search(0, 1)] == ["a"]
    assert {s.sample_id for _, s in tree.search(0, 2)} == {"a", "b"}


def test_repeated_and_resized_visuals_have_stable_hashes(tmp_path: Path) -> None:
    original = tmp_path / "original.jpg"
    resized = tmp_path / "resized.jpg"
    make_image(original, (40, 100, 180), (80, 80))
    with Image.open(original) as image:
        image.resize((160, 160), Image.Resampling.BICUBIC).save(resized, format="JPEG")
    assert dhash64(original) == dhash64(resized)


def test_parallel_and_serial_candidate_results_match(tmp_path: Path) -> None:
    dataset = tmp_path / "datasets"; dataset.mkdir()
    make_image(dataset / "a.jpg", (40, 100, 180))
    make_image(dataset / "b.jpg", (40, 100, 180), (80, 80))
    rows = [
        row("a", "a.jpg", hashlib.sha256(b"a").hexdigest(), "train"),
        row("b", "b.jpg", hashlib.sha256(b"b").hexdigest(), "unassigned"),
    ]
    source = manifest(dataset, rows)
    protected = tmp_path / "protected.json"
    protected.write_text('{"source_manifest_sha256": "' + hashlib.sha256(source.read_bytes()).hexdigest() + '"}')
    from scripts.audit_near_duplicates import load_samples, candidate_rows
    samples, _ = load_samples(source, dataset)
    assert candidate_rows(samples, dataset, 6, workers=1) == candidate_rows(samples, dataset, 6, workers=2)


def test_full_audit_includes_unassigned_and_cross_split_candidate(tmp_path: Path) -> None:
    dataset = tmp_path / "datasets"
    dataset.mkdir()
    make_image(dataset / "a.jpg", (40, 100, 180))
    make_image(dataset / "b.jpg", (40, 100, 180), (80, 80))
    rows = [
        row("a", "a.jpg", hashlib.sha256(b"a").hexdigest(), "train"),
        row("b", "b.jpg", hashlib.sha256(b"b").hexdigest(), "unassigned"),
    ]
    source = manifest(dataset, rows)
    protected = tmp_path / "protected.json"
    protected.write_text('{"source_manifest_sha256": "' + hashlib.sha256(source.read_bytes()).hexdigest() + '"}')
    output = tmp_path / "candidates.json"
    output_csv = tmp_path / "candidates.csv"
    assert main([
        "--manifest", str(source), "--dataset-root", str(dataset),
        "--protected-metadata", str(protected), "--output-json", str(output),
        "--output-csv", str(output_csv), "--threshold", "6",
    ]) == 0
    data = output.read_text(encoding="utf-8")
    assert '"sample_count": 2' in data
    assert '"candidate_unreviewed"' in data
    assert '"cross_split": true' in data
    assert ALGORITHM in data
    assert source.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")


def test_refuses_existing_outputs_and_manifest_mismatch(tmp_path: Path) -> None:
    dataset = tmp_path / "datasets"; dataset.mkdir()
    make_image(dataset / "a.jpg", (1, 2, 3))
    source = manifest(dataset, [row("a", "a.jpg", "a" * 64, "train")])
    protected = tmp_path / "protected.json"
    protected.write_text('{"source_manifest_sha256": "wrong"}')
    output = tmp_path / "candidates.json"
    assert main([
        "--manifest", str(source), "--dataset-root", str(dataset),
        "--protected-metadata", str(protected), "--output-json", str(output),
        "--output-csv", str(tmp_path / "candidates.csv"),
    ]) == 3
    output.write_text("sentinel")
    protected.write_text('{"source_manifest_sha256": "' + hashlib.sha256(source.read_bytes()).hexdigest() + '"}')
    assert main([
        "--manifest", str(source), "--dataset-root", str(dataset),
        "--protected-metadata", str(protected), "--output-json", str(output),
        "--output-csv", str(tmp_path / "candidates.csv"),
    ]) == 4
    assert output.read_text() == "sentinel"
