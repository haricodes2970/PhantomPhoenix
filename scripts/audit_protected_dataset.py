"""Read-only protected-dataset integrity and leakage audit.

This tool never rewrites the source manifest or assigns unassigned samples.
It can create a protection snapshot only when all currently assigned rows pass
strict integrity checks.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from PIL import Image

TOOL_VERSION = "1.0.0"
SCHEMA_VERSION = "protected-dataset-snapshot-v1"
REQUIRED_COLUMNS = {
    "sample_id", "relative_path", "label", "original_dataset",
    "original_revision", "original_sample_id", "generator_family",
    "original_format", "sha256", "license_ref", "download_status", "split",
}
SNAPSHOT_COLUMNS = [
    "sample_id", "sha256", "relative_path", "label", "original_dataset",
    "original_revision", "original_sample_id", "generator_family",
    "original_format", "original_split",
]
ASSIGNED_SPLITS = {"train", "val", "test"}
VALID_LABELS = {"real", "ai_generated"}


def sha256_file(path: Path) -> str:
    """Return SHA-256 for a file without modifying it."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_snapshot_bytes(rows: Iterable[dict[str, str]]) -> bytes:
    """Canonicalize snapshot rows for deterministic hashing.

    Rows are sorted by sample_id. Columns and order are fixed. UTF-8 encoding,
    LF line endings, and unit-separator field delimiters are intentional.
    """
    ordered = sorted(rows, key=lambda row: row["sample_id"])
    lines = ["\x1f".join(row[column] for column in SNAPSHOT_COLUMNS) for row in ordered]
    return ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")


def snapshot_digest(rows: Iterable[dict[str, str]]) -> str:
    """Return deterministic SHA-256 digest of canonical snapshot data."""
    return hashlib.sha256(canonical_snapshot_bytes(rows)).hexdigest()


def safe_dataset_path(dataset_root: Path, relative_path: str) -> tuple[Path | None, str | None]:
    """Resolve a manifest path and reject absolute or escaping paths."""
    candidate = Path(relative_path)
    if candidate.is_absolute():
        return None, "absolute relative_path"
    root = dataset_root.resolve()
    resolved = (root / candidate).resolve()
    if resolved != root and root not in resolved.parents:
        return None, "path escapes dataset root"
    return resolved, None


def load_manifest(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    """Load manifest rows and return schema errors without changing the file."""
    errors: list[str] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - columns)
        if missing:
            errors.append(f"missing required columns: {', '.join(missing)}")
        rows = list(reader)
    return rows, errors


def validate_rows(
    rows: list[dict[str, str]], dataset_root: Path, *, assigned_only: bool
) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate rows; continue diagnostics after independent row failures."""
    errors: list[str] = []
    diagnostics: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        split = row.get("split", "")
        if assigned_only and split not in ASSIGNED_SPLITS:
            continue
        prefix = f"row {index} sample {row.get('sample_id', '<missing>')}"
        for field in REQUIRED_COLUMNS:
            if not row.get(field, "").strip():
                errors.append(f"{prefix}: missing {field}")
        if row.get("label") not in VALID_LABELS:
            errors.append(f"{prefix}: invalid label {row.get('label')!r}")
        if assigned_only and split not in ASSIGNED_SPLITS:
            errors.append(f"{prefix}: invalid assigned split {split!r}")
        path, path_error = safe_dataset_path(dataset_root, row.get("relative_path", ""))
        if path_error:
            errors.append(f"{prefix}: {path_error}")
        elif path is not None and not path.is_file():
            errors.append(f"{prefix}: missing file {row.get('relative_path')}")
        elif path is not None:
            try:
                with Image.open(path) as image:
                    image.verify()
                with Image.open(path) as image:
                    width, height = image.size
                diagnostics.append({
                    "sample_id": row.get("sample_id"),
                    "split": split,
                    "label": row.get("label"),
                    "format": row.get("original_format"),
                    "width": width,
                    "height": height,
                })
            except Exception as exc:
                errors.append(f"{prefix}: corrupt/unreadable image ({type(exc).__name__})")
    return diagnostics, errors


def duplicate_errors(rows: list[dict[str, str]], assigned_only: bool) -> list[str]:
    """Find duplicate IDs/hashes and cross-split exact-hash conflicts."""
    selected = [r for r in rows if not assigned_only or r.get("split") in ASSIGNED_SPLITS]
    errors: list[str] = []
    for field in ("sample_id", "sha256"):
        groups: dict[str, list[str]] = defaultdict(list)
        for row in selected:
            value = row.get(field, "")
            if value:
                groups[value].append(row.get("sample_id", "<missing>"))
        for value, ids in groups.items():
            if len(ids) > 1:
                errors.append(f"duplicate {field} {value}: {','.join(ids)}")
    hashes: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for row in selected:
        hashes[row.get("sha256", "")].append((row.get("sample_id", ""), row.get("split", "")))
    for digest, members in hashes.items():
        if len({split for _, split in members}) > 1:
            errors.append(f"cross-split exact-hash conflict {digest}: {members}")
    return errors


def counts(rows: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    """Return split and label counts."""
    split_counts = Counter(row.get("split", "unassigned") for row in rows)
    label_counts = Counter(row.get("label", "unknown") for row in rows)
    return {"splits": dict(sorted(split_counts.items())), "labels": dict(sorted(label_counts.items()))}


def distribution(rows: list[dict[str, str]], dataset_root: Path) -> dict[str, Any]:
    """Return confounding distributions without interpretation."""
    result: dict[str, Any] = {}
    for field in ("label", "split", "original_dataset", "original_revision", "generator_family", "original_format"):
        result[field] = dict(Counter(row.get(field, "unknown") or "unknown" for row in rows).most_common())
    dimensions: Counter[str] = Counter()
    dimension_errors = 0
    for row in rows:
        path, error = safe_dataset_path(dataset_root, row.get("relative_path", ""))
        if error or path is None:
            continue
        try:
            with Image.open(path) as image:
                dimensions[f"{image.width}x{image.height}"] += 1
        except Exception:
            dimension_errors += 1
    result["dimensions_top"] = dict(dimensions.most_common(30))
    result["dimension_read_errors"] = dimension_errors
    result["label_by_format"] = _cross_counts(rows, "label", "original_format")
    result["split_by_format"] = _cross_counts(rows, "split", "original_format")
    result["split_by_generator_family"] = _cross_counts(rows, "split", "generator_family")
    return result


def _cross_counts(rows: list[dict[str, str]], outer: str, inner: str) -> dict[str, dict[str, int]]:
    table: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        table[row.get(outer, "unknown")][row.get(inner, "unknown")] += 1
    return {key: dict(value) for key, value in sorted(table.items())}


def write_new(path: Path, data: str) -> None:
    """Write only when output does not already exist."""
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8", newline="")


def build_snapshot(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Build assigned-only snapshot rows preserving original split."""
    return [
        {**{column: row.get(column, "") for column in SNAPSHOT_COLUMNS[:-1]}, "original_split": row["split"]}
        for row in rows if row.get("split") in ASSIGNED_SPLITS
    ]


def main(argv: list[str] | None = None) -> int:
    """Run audit and optionally create a protected snapshot."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("datasets/manifests/dataset_manifest.csv"))
    parser.add_argument("--dataset-root", type=Path, default=Path("datasets"))
    parser.add_argument("--snapshot-csv", type=Path, default=Path("datasets/provenance/protected_dataset_snapshot.csv"))
    parser.add_argument("--snapshot-metadata", type=Path, default=Path("datasets/provenance/protected_dataset_snapshot.json"))
    parser.add_argument("--report", type=Path, default=Path("docs/PROTECTED_DATASET_AUDIT.md"))
    parser.add_argument("--verify-snapshot", action="store_true")
    args = parser.parse_args(argv)

    if not args.manifest.is_file():
        print(f"Manifest not found: {args.manifest}", file=sys.stderr)
        return 2
    rows, schema_errors = load_manifest(args.manifest)
    all_errors = list(schema_errors)
    assigned = [row for row in rows if row.get("split") in ASSIGNED_SPLITS]
    unassigned = [row for row in rows if row.get("split") not in ASSIGNED_SPLITS]
    assigned_diagnostics, assigned_errors = validate_rows(rows, args.dataset_root, assigned_only=True)
    _, diagnostic_errors = validate_rows(rows, args.dataset_root, assigned_only=False)
    all_errors.extend(assigned_errors)
    all_errors.extend(duplicate_errors(rows, assigned_only=True))

    source_digest = sha256_file(args.manifest)
    snapshot_rows = build_snapshot(rows)
    canonical_digest = snapshot_digest(snapshot_rows)
    counts_data = counts(rows)
    distributions = distribution(rows, args.dataset_root)
    timestamp = datetime.now(timezone.utc).isoformat()

    if args.verify_snapshot:
        if not args.snapshot_csv.is_file() or not args.snapshot_metadata.is_file():
            print("Snapshot verification failed: snapshot files missing", file=sys.stderr)
            return 3
        with args.snapshot_csv.open("r", encoding="utf-8", newline="") as handle:
            existing = list(csv.DictReader(handle))
        metadata = json.loads(args.snapshot_metadata.read_text(encoding="utf-8"))
        verification_errors: list[str] = []
        if metadata.get("source_manifest_sha256") != source_digest:
            verification_errors.append("source manifest SHA-256 changed")
        if metadata.get("canonical_data_digest") != snapshot_digest(existing):
            verification_errors.append("snapshot canonical digest mismatch")
        if verification_errors:
            print("Snapshot verification failed: " + "; ".join(verification_errors), file=sys.stderr)
            return 3
        print("Snapshot verification passed")
        return 0

    if all_errors:
        print(f"Protection snapshot NOT created: {len(all_errors)} assigned-row invariant errors", file=sys.stderr)
    else:
        if args.snapshot_csv.exists() or args.snapshot_metadata.exists():
            print("Protection snapshot NOT created: output already exists", file=sys.stderr)
            return 4
        output = io_csv(snapshot_rows)
        metadata = {
            "schema_version": SCHEMA_VERSION,
            "tool_version": TOOL_VERSION,
            "created_at_utc": timestamp,
            "source_manifest": str(args.manifest),
            "source_manifest_sha256": source_digest,
            "source_manifest_row_count": len(rows),
            "assigned_row_count": len(assigned),
            "unassigned_row_count": len(unassigned),
            "counts": counts_data,
            "canonicalization": {
                "columns": SNAPSHOT_COLUMNS,
                "sort_key": "sample_id ascending",
                "encoding": "UTF-8",
                "line_endings": "LF",
                "delimiter": "ASCII unit separator (U+001F)",
                "hash": "SHA-256",
            },
            "canonical_data_digest": canonical_digest,
        }
        write_new(args.snapshot_csv, output)
        write_new(args.snapshot_metadata, json.dumps(metadata, indent=2) + "\n")
        print(f"Protection snapshot created: {args.snapshot_csv}")

    report = render_report(args, rows, assigned, unassigned, all_errors, diagnostic_errors, counts_data, distributions, source_digest, canonical_digest, timestamp)
    try:
        write_new(args.report, report)
    except FileExistsError:
        print(f"Refusing to overwrite existing report: {args.report}", file=sys.stderr)
        return 4
    print(f"Audit report created: {args.report}")
    return 1 if all_errors else 0


def io_csv(rows: list[dict[str, str]]) -> str:
    """Serialize snapshot rows deterministically as CSV."""
    import io
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=SNAPSHOT_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(sorted(rows, key=lambda row: row["sample_id"]))
    return stream.getvalue()


def render_report(args: argparse.Namespace, rows: list[dict[str, str]], assigned: list[dict[str, str]], unassigned: list[dict[str, str]], errors: list[str], diagnostic_errors: list[str], count_data: dict[str, dict[str, int]], distributions: dict[str, Any], source_digest: str, canonical_digest: str, timestamp: str) -> str:
    """Render a reviewable Markdown audit report."""
    status = "FAILED — protection snapshot not created" if errors else "PASSED — protection snapshot created"
    lines = [
        "# Protected Dataset Integrity and Leakage Audit",
        "",
        f"**Status:** {status}",
        f"**Tool version:** `{TOOL_VERSION}`  ",
        f"**Created:** `{timestamp}`  ",
        f"**Source manifest:** `{args.manifest}`  ",
        f"**Source manifest SHA-256:** `{source_digest}`",
        "",
        "## Inventory",
        f"- Manifest rows: **{len(rows)}**",
        f"- Assigned rows: **{len(assigned)}**",
        f"- Unassigned rows: **{len(unassigned)}** (untouched)",
        f"- Labels: `{count_data['labels']}`",
        f"- Splits: `{count_data['splits']}`",
        f"- Exact-hash uniqueness: `{len({r.get('sha256') for r in rows})}` unique hashes",
        "",
        "## Protection artifact",
        f"- Canonical digest: `{canonical_digest}`",
        f"- Snapshot path: `{args.snapshot_csv}` (created only when invariants pass)",
        f"- Snapshot schema: `{SCHEMA_VERSION}`",
        f"- Source manifest row count: **{len(rows)}**",
        f"- Assigned split counts: `{count_data['splits']}`",
        f"- Label counts: `{count_data['labels']}`",
        "- Snapshot includes assigned rows only; no rows were assigned by this audit.",
        "- The snapshot is integrity-checkable, not cryptographically immutable.",
        "",
        "## Confounding observations",
        "- `original_dataset` and `original_revision` are dataset-provided metadata, not independent provenance verification.",
        f"- Generator/source distribution: `{distributions['generator_family']}`",
        f"- Format distribution: `{distributions['original_format']}`",
        f"- Label by format: `{distributions['label_by_format']}`",
        f"- Split by format: `{distributions['split_by_format']}`",
        f"- Split by generator family: `{distributions['split_by_generator_family']}`",
        f"- Dimensions (top buckets): `{distributions['dimensions_top']}`",
        "- Resolution buckets were computed from local files; distributions are observations, not causal explanations.",
        "",
        "## Duplicate and leakage findings",
        "- Exact duplicate IDs/hashes and assigned cross-split exact-hash conflicts are fatal protection errors if present.",
        "- Near-duplicate detection was **not executed**; no approved existing perceptual-hash dependency was used.",
        "- Near-duplicate review remains required before assigning unassigned rows.",
        "",
        "## Diagnostics",
        f"- Assigned-row protection errors: **{len(errors)}**",
        f"- Full diagnostic row errors: **{len(diagnostic_errors)}**",
    ]
    if errors:
        lines += ["", "### Protection errors", *[f"- {error}" for error in errors[:100]]]
    if diagnostic_errors:
        lines += ["", "### Diagnostic errors", *[f"- {error}" for error in diagnostic_errors[:100]]]
    lines += [
        "",
        "## Proposed future strategy (not assignment)",
        "1. Freeze the original assigned rows and test hashes as the historical baseline.",
        "2. Cluster exact and near duplicates across all rows before assigning anything new.",
        "3. Keep duplicate clusters within one future split.",
        "4. Review ambiguous labels and provenance before eligibility.",
        "5. Use separate source-held-out and generator-family-held-out evaluations.",
        "6. Select thresholds on validation only, then run one frozen test evaluation.",
        "7. Require fixed seeds and versioned manifests for any future assignment.",
        "",
        "## Research readiness",
        "- Google-, OpenAI-, and Midjourney-associated families are dataset-provided labels where present; independent provenance is unknown.",
        "- Future collection requires source URL/repository, exact family/version, license, transformation history, and label evidence.",
        "",
        "## Limitations and approval decisions",
        "- No actual split assignments were generated.",
        "- No near-duplicate claims are made.",
        "- Source-held-out and generator-held-out partitions require project-lead approval after grouping review.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
