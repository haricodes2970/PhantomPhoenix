"""Prepare a deterministic, local-only review queue for dHash candidates."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
from pathlib import Path
from typing import Any


TOOL_VERSION = "1.0.0"
REVIEW_STATUS = "pending"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_candidate_id(candidate: dict[str, Any]) -> str:
    """Derive stable ID from candidate kind and ordered sample IDs."""
    pair = "\x1f".join((str(candidate["kind"]), *sorted((str(candidate["sample_a"]), str(candidate["sample_b"]))))).encode()
    return "cand_" + hashlib.sha256(pair).hexdigest()[:16]


def safe_path(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    if candidate.is_absolute() or (resolved != resolved_root and resolved_root not in resolved.parents):
        raise ValueError(f"path escapes dataset root: {relative}")
    if not resolved.is_file():
        raise ValueError(f"missing candidate image: {relative}")
    return resolved


def load_candidate_files(path_json: Path, path_csv: Path) -> list[dict[str, Any]]:
    data = json.loads(path_json.read_text(encoding="utf-8"))
    candidates = data.get("candidates", [])
    with path_csv.open(encoding="utf-8", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    json_keys = {(x.get("kind"), x.get("sample_a"), x.get("sample_b")) for x in candidates}
    csv_keys = {(x.get("kind"), x.get("sample_a"), x.get("sample_b")) for x in csv_rows}
    if json_keys != csv_keys or len(candidates) != len(csv_rows):
        raise ValueError("candidate JSON and CSV disagree")
    return candidates


def build_queue(candidates: list[dict[str, Any]], manifest: dict[str, dict[str, str]], root: Path) -> list[dict[str, str]]:
    queue: list[dict[str, str]] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate_id = stable_candidate_id(candidate)
        if candidate_id in seen:
            raise ValueError(f"duplicate candidate ID: {candidate_id}")
        seen.add(candidate_id)
        first = manifest.get(str(candidate["sample_a"]))
        second = manifest.get(str(candidate["sample_b"]))
        if first is None or second is None:
            raise ValueError("candidate references unknown sample ID")
        for suffix, row, expected_hash in (("a", first, candidate.get("sha256_a")), ("b", second, candidate.get("sha256_b"))):
            if expected_hash is not None and expected_hash != row["sha256"]:
                raise ValueError(f"candidate hash mismatch for sample {row['sample_id']}")
            safe_path(root, row["relative_path"])
        cross = first["split"] != second["split"]
        queue.append({
            "candidate_id": candidate_id,
            "kind": str(candidate["kind"]),
            "sample_a": first["sample_id"], "sample_b": second["sample_id"],
            "sha256_a": first["sha256"], "sha256_b": second["sha256"],
            "relative_path_a": first["relative_path"], "relative_path_b": second["relative_path"],
            "split_a": first["split"], "split_b": second["split"],
            "label_a": first["label"], "label_b": second["label"],
            "family_a": first.get("generator_family", "unknown"),
            "family_b": second.get("generator_family", "unknown"),
            "distance": str(candidate.get("distance", "")),
            "cross_split": str(cross).lower(),
            "unassigned_involvement": str(first["split"] == "unassigned" or second["split"] == "unassigned").lower(),
            "review_status": REVIEW_STATUS,
            "reviewer_decision": "",
            "reviewer": "",
            "review_date_utc": "",
            "reviewer_notes": "",
        })
    return sorted(queue, key=lambda row: row["candidate_id"])


def write_new(path: Path, content: str | bytes) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8", newline="")


def render_html(queue: list[dict[str, str]], dataset_root: Path) -> str:
    cards: list[str] = []
    for row in queue:
        image_a = "../../" + row["relative_path_a"]
        image_b = "../../" + row["relative_path_b"]
        badge = "CROSS-SPLIT" if row["cross_split"] == "true" else "same split"
        unassigned = " · UNASSIGNED INVOLVED" if row["unassigned_involvement"] == "true" else ""
        cards.append(f"""<article class="card">
<h2>{html.escape(row['candidate_id'])} <span>{html.escape(badge)}{html.escape(unassigned)}</span></h2>
<div class="meta">dHash distance: <b>{html.escape(row['distance'])}</b> · status: <b>candidate_unreviewed</b></div>
<div class="pair"><figure><img src="{html.escape(image_a)}" loading="lazy"><figcaption>{html.escape(row['sample_a'])}<br>split={html.escape(row['split_a'])} · label={html.escape(row['label_a'])}<br>family={html.escape(row['family_a'])}</figcaption></figure>
<figure><img src="{html.escape(image_b)}" loading="lazy"><figcaption>{html.escape(row['sample_b'])}<br>split={html.escape(row['split_b'])} · label={html.escape(row['label_b'])}<br>family={html.escape(row['family_b'])}</figcaption></figure></div>
<p>Review externally in the CSV queue. Do not infer shared provenance from visual similarity alone.</p>
</article>""")
    return """<!doctype html><html><head><meta charset="utf-8"><title>PHANTOM PHOENIX Near-Duplicate Review</title>
<style>body{font:14px system-ui;background:#111;color:#eee;margin:24px}.card{border:1px solid #555;padding:16px;margin:16px 0;max-width:1100px}.pair{display:flex;gap:18px;flex-wrap:wrap}figure{margin:0;width:min(48%,520px)}img{width:100%;max-height:480px;object-fit:contain;background:#222}figcaption{line-height:1.5}.meta{color:#bbb}h2 span{font-size:12px;color:#f6c85f;margin-left:10px}</style></head>
<body><h1>PHANTOM PHOENIX — Near-Duplicate Candidate Review</h1><p>Local-only review page. Candidates are unreviewed; no split or label decisions are made here.</p>
""" + "\n".join(cards) + "</body></html>"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("datasets/manifests/dataset_manifest.csv"))
    parser.add_argument("--dataset-root", type=Path, default=Path("datasets"))
    parser.add_argument("--candidates-json", type=Path, default=Path("datasets/provenance/near_duplicate_candidates_v1.json"))
    parser.add_argument("--candidates-csv", type=Path, default=Path("datasets/provenance/near_duplicate_candidates_v1.csv"))
    parser.add_argument("--protected-metadata", type=Path, default=Path("datasets/provenance/protected_dataset_snapshot.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("datasets/provenance/near_duplicate_review_v1"))
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        print(f"refusing to overwrite existing output directory: {args.output_dir}")
        return 4
    metadata = json.loads(args.protected_metadata.read_text(encoding="utf-8"))
    if sha256_file(args.manifest) != metadata.get("source_manifest_sha256"):
        print("source manifest differs from protected snapshot")
        return 3
    rows = {row["sample_id"]: row for row in csv.DictReader(args.manifest.open(encoding="utf-8", newline=""))}
    candidates = load_candidate_files(args.candidates_json, args.candidates_csv)
    queue = build_queue(candidates, rows, args.dataset_root)
    fields = list(queue[0]) if queue else []
    import io
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader(); writer.writerows(queue)
    write_new(args.output_dir / "near_duplicate_review_queue_v1.csv", stream.getvalue())
    write_new(args.output_dir / "index.html", render_html(queue, args.dataset_root))
    write_new(args.output_dir / "review_guide.md", """# Review guide

Decisions:

- `same_image_transform`: strong evidence same image with resize/recompression/minor transformation.
- `near_duplicate_related`: related derivative, but not clearly same image.
- `visually_similar_unrelated`: similar appearance without sufficient same-origin evidence.
- `uncertain`: insufficient evidence.
- `unreviewed`: no decision yet.

Style, subject, composition, or generator-family similarity alone is not sufficient evidence of shared provenance. Record reviewer, UTC date, decision, and concise rationale in the CSV. Do not edit production manifest or split assignments during review.
""")
    print(f"created review queue with {len(queue)} candidates")
    print(f"open locally: {args.output_dir / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
