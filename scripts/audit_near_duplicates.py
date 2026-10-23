"""Read-only perceptual near-duplicate candidate audit.

Uses a dependency-free 64-bit dHash implementation based on Pillow. Results are
candidate similarities only; they are not confirmed duplicates or leakage.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from PIL import Image

TOOL_VERSION = "1.0.0"
ALGORITHM = "dHash-64"
DEFAULT_THRESHOLD = 6


@dataclass(frozen=True)
class Sample:
    sample_id: str
    sha256: str
    relative_path: str
    label: str
    split: str
    generator_family: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dhash64(path: Path) -> int:
    """Compute 64-bit horizontal gradient hash from a local image."""
    with Image.open(path) as image:
        gray = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
        pixels = list(gray.getdata())
    value = 0
    for row in range(8):
        for col in range(8):
            value = (value << 1) | int(pixels[row * 9 + col] > pixels[row * 9 + col + 1])
    return value


def hamming_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()


class BKTree:
    """Deterministic BK-tree for Hamming-distance candidate lookup."""

    def __init__(self) -> None:
        self.root: tuple[int, Sample, dict[int, tuple[int, Sample, dict]]] | None = None

    def add(self, value: int, sample: Sample) -> None:
        if self.root is None:
            self.root = (value, sample, {})
            return
        node = self.root
        while True:
            distance = hamming_distance(value, node[0])
            child = node[2].get(distance)
            if child is None:
                node[2][distance] = (value, sample, {})
                return
            node = child

    def search(self, value: int, threshold: int) -> list[tuple[int, Sample]]:
        results: list[tuple[int, Sample]] = []

        def visit(node: tuple[int, Sample, dict[int, tuple[int, Sample, dict]]]) -> None:
            distance = hamming_distance(value, node[0])
            if distance <= threshold:
                results.append((distance, node[1]))
            low, high = distance - threshold, distance + threshold
            for edge, child in node[2].items():
                if low <= edge <= high:
                    visit(child)

        if self.root is not None:
            visit(self.root)
        return results


def load_samples(manifest: Path, dataset_root: Path) -> tuple[list[Sample], str]:
    source_digest = sha256_file(manifest)
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"sample_id", "sha256", "relative_path", "label", "split", "generator_family"}
    missing = required - set(rows[0] if rows else [])
    if missing:
        raise ValueError(f"Manifest missing required columns: {sorted(missing)}")
    samples: list[Sample] = []
    for row in rows:
        path = Path(row["relative_path"])
        resolved_root = dataset_root.resolve()
        resolved = (resolved_root / path).resolve()
        if path.is_absolute() or (resolved != resolved_root and resolved_root not in resolved.parents):
            raise ValueError(f"Path escapes dataset root: {row['sample_id']}")
        if not resolved.is_file():
            raise ValueError(f"Missing image: {row['sample_id']}")
        samples.append(Sample(
            sample_id=row["sample_id"], sha256=row["sha256"],
            relative_path=row["relative_path"], label=row["label"],
            split=row.get("split", "unassigned"),
            generator_family=row.get("generator_family", "unknown"),
        ))
    return samples, source_digest


def candidate_rows(
    samples: list[Sample], dataset_root: Path, threshold: int, workers: int = 1
) -> list[dict[str, object]]:
    """Generate candidates with deterministic sample ordering and optional hash parallelism."""
    ordered = sorted(samples, key=lambda item: item.sample_id)
    paths = [(dataset_root / sample.relative_path).resolve() for sample in ordered]
    if workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            values = list(executor.map(dhash64, paths))
    else:
        values = [dhash64(path) for path in paths]

    tree = BKTree()
    hashes: dict[str, Sample] = {}
    output: list[dict[str, object]] = []
    for sample, value in zip(ordered, values):
        if sample.sha256 in hashes:
            output.append({"kind": "exact_sha256", "status": "verified_exact", "sample_a": hashes[sample.sha256].sample_id, "sample_b": sample.sample_id, "distance": 0})
        hashes[sample.sha256] = sample
        for distance, other in tree.search(value, threshold):
            if other.sha256 == sample.sha256:
                continue
            first, second = sorted((other, sample), key=lambda item: item.sample_id)
            output.append({
                "kind": "perceptual_candidate", "status": "candidate_unreviewed",
                "algorithm": ALGORITHM, "threshold": threshold,
                "sample_a": first.sample_id, "sample_b": second.sample_id,
                "sha256_a": first.sha256, "sha256_b": second.sha256,
                "split_a": first.split, "split_b": second.split,
                "label_a": first.label, "label_b": second.label,
                "family_a": first.generator_family, "family_b": second.generator_family,
                "distance": distance,
                "cross_split": first.split != second.split,
            })
        tree.add(value, sample)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("datasets/manifests/dataset_manifest.csv"))
    parser.add_argument("--dataset-root", type=Path, default=Path("datasets"))
    parser.add_argument("--protected-metadata", type=Path, default=Path("datasets/provenance/protected_dataset_snapshot.json"))
    parser.add_argument("--output-json", type=Path, default=Path("datasets/provenance/near_duplicate_candidates.json"))
    parser.add_argument("--output-csv", type=Path, default=Path("datasets/provenance/near_duplicate_candidates.csv"))
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    args = parser.parse_args(argv)
    if args.threshold < 0 or args.threshold > 64:
        parser.error("--threshold must be between 0 and 64")
    if args.workers < 1 or args.workers > 64:
        parser.error("--workers must be between 1 and 64")
    if args.output_json.exists() or args.output_csv.exists():
        print("Refusing to overwrite existing output", flush=True)
        return 4
    if not args.protected_metadata.is_file():
        print("Protected snapshot metadata is required", flush=True)
        return 2
    metadata = json.loads(args.protected_metadata.read_text(encoding="utf-8"))
    source_digest = sha256_file(args.manifest)
    if metadata.get("source_manifest_sha256") != source_digest:
        print("Source manifest differs from protected snapshot", flush=True)
        return 3
    with args.manifest.open("r", encoding="utf-8", newline="") as handle:
        samples, _ = load_samples(args.manifest, args.dataset_root)
    started = datetime.now(timezone.utc).isoformat()
    candidates = candidate_rows(samples, args.dataset_root, args.threshold, args.workers)
    payload = {
        "tool_version": TOOL_VERSION, "algorithm": ALGORITHM,
        "threshold": args.threshold, "workers": args.workers, "created_at_utc": started,
        "source_manifest": str(args.manifest), "source_manifest_sha256": source_digest,
        "sample_count": len(samples), "candidate_count": len(candidates),
        "perceptual_candidates_are_unreviewed": True, "candidates": candidates,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with args.output_csv.open("w", encoding="utf-8", newline="") as handle:
        fields = sorted({key for item in candidates for key in item}) or ["kind"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(candidates)
    print(f"Audited {len(samples)} samples; candidates={len(candidates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
