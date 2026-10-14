# ML environment setup

Isolated detector environment for PHANTOM PHOENIX. Does not modify system Python.

Checked 2026-10-14 against the machine and the candidate checkpoint:

| Piece | Pin | Why |
|---|---|---|
| Python | 3.12 | System Python is 3.14. CUDA torch wheels exist for 3.12 and are not experimental there. |
| torch / torchvision | 2.11.0+cu128 | Official `cu128` index has `cp312` manylinux x86_64 wheels. Driver 610.43.03 reports CUDA UMD 13.3, which is new enough to load a CUDA 12.8 wheel. |
| transformers | `>=5.10.0,<5.20.0` | Candidate preprocessor uses `size.shortest_edge` and crashes below 5.4.0. Versions below 5.10.0 are affected by GHSA-xrqw-3rrv-vx5w. |
| Model | `buildborderless/CommunityForensics-DeepfakeDet-ViT` | Provisional primary. Not swapped if it fails. |

`torch` is installed from the PyTorch index, not from PyPI. A PyPI `torch` install on Linux is CPU-only.

## Candidate semantics (this checkpoint only)

Verified from the model card and from `config.json` / `preprocessor_config.json` before install:

- Architecture: ViT-Small, `num_attention_heads=6`, `image_size=384`, `num_labels=1`.
- Preprocess: shortest edge resized to 440, center crop 384, CLIP mean/std.
- Output: **one logit**. `sigmoid(logit)` is the fake probability. This is not a two-class softmax. Other detectors do not share this mapping.
- The smoke test refuses to score an image if the loaded config does not match those three values.

A smoke test does not measure accuracy.

## Create the environment

From the repository root. Requires [uv](https://docs.astral.sh/uv/) and an NVIDIA driver. Does not install a CUDA toolkit.

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python \
  torch==2.11.0+cu128 torchvision==0.26.0+cu128 \
  --index-url https://download.pytorch.org/whl/cu128
uv pip install --python .venv/bin/python -r requirements-ml.txt
uv pip install --python .venv/bin/python -r requirements-api.txt
```

`.venv/` and the Hugging Face weight cache are gitignored. Weights download on the first smoke test into the default Hugging Face cache (`~/.cache/huggingface`), which is outside this repo.

## Smoke test (standalone detector)

Supply a real local image. The script does not download or fabricate one.

```bash
.venv/bin/python scripts/smoke_detector.py --image /path/to/image.jpg
```

`--device auto` (default) tries CUDA, then CPU if CUDA is missing or the CUDA forward pass throws. `--device cuda` and `--device cpu` do not fall back.

Exit codes:

| Code | Meaning |
|---|---|
| 0 | One real forward pass finished. |
| 2 | No image supplied, or the path is not a file. No prediction. |
| 1 | Import, weight download, config mismatch, or inference failed. The candidate was not replaced. |

JSON includes Python, torch, transformers, `cuda_available`, `gpu_name`, model id, loaded config, input width/height, raw logit, sigmoid fake probability, device actually used, and duration. `accuracy_claim` is always `null`.

## Start the API server

```bash
.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Or with reload for development:

```bash
.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Service health and detector status |
| POST | `/api/scans` | Upload image for AI detection (multipart/form-data) |
| GET | `/api/scans` | Scan history (not implemented - requires DB) |
| GET | `/api/scans/{id}` | Get scan by ID (not implemented - requires DB) |

### POST `/api/scans` Request

- Multipart form field: `file`
- Allowed formats: JPEG, PNG, WEBP (validated by decode, not extension)
- Max size: 15 MiB
- Max dimensions: 8192 px per side

### POST `/api/scans` Response (201 Created)

```json
{
  "scan_id": "uuid",
  "status": "complete|failed",
  "result": {
    "scan_id": "uuid",
    "created_at": "ISO8601",
    "status": "complete|failed",
    "input": {
      "sha256": "hex",
      "filename": "original.jpg",
      "media_type": "image/jpeg",
      "byte_size": 12345,
      "width": 512,
      "height": 512
    },
    "models": [
      {
        "model_id": "buildborderless/CommunityForensics-DeepfakeDet-ViT",
        "model_revision": "...",
        "role": "primary",
        "status": "ok|error",
        "fake_probability": 0.0044,
        "raw_logit": -5.42,
        "threshold_policy": "0.80 likely_ai / 0.20 likely_real",
        "limitations": ["Not calibrated on images from this deployment", "..."],
        "device": "cuda|cpu",
        "duration_seconds": 0.19
      }
    ],
    "indicators": [
      {
        "id": "metadata",
        "method": "computed",
        "status": "ok",
        "value": {
          "result": {"format": "JPEG", "width": 512, "height": 512, "has_exif": false, ...},
          "evidence_category": "computed",
          "limitations": ["Absence of EXIF is common in web images..."],
          "error": null
        },
        "note": "Image format is JPEG (512x512, mode RGB). EXIF metadata is absent."
      },
      {
        "id": "ela",
        "method": "computed",
        "status": "ok",
        "value": {
          "result": {"mean_difference": 1.23, "max_difference": 45.0, "std_difference": 3.45},
          "evidence_category": "computed",
          "limitations": ["ELA is a heuristic visualization tool..."],
          "error": null
        },
        "note": "ELA mean difference is 1.23 (std 3.45). ...",
        "artifact": "uploads/artifacts/scan_id/ela.jpg"
      },
      {
        "id": "noise",
        "method": "heuristic",
        "status": "ok",
        "value": {
          "result": {"noise_std": 8.9, "noise_mean": -0.1, "noise_max": 42.3},
          "evidence_category": "heuristic",
          "limitations": ["Noise residuals are heuristic estimates..."],
          "error": null
        },
        "note": "Noise standard deviation is 8.90 (mean -0.10). ...",
        "artifact": "uploads/artifacts/scan_id/noise.jpg"
      },
      {
        "id": "frequency",
        "method": "computed",
        "status": "ok",
        "value": {
          "result": {"mean_magnitude": 24.5, "std_magnitude": 8.2, "max_magnitude": 65.3},
          "evidence_category": "computed",
          "limitations": ["Frequency domain analysis reveals spectral energy..."],
          "error": null
        },
        "note": "Frequency spectrum mean log-magnitude is 24.50 (std 8.20). ...",
        "artifact": "uploads/artifacts/scan_id/fft.jpg"
      }
    ],
    "explainability": {"status": "unavailable", "kind": null, "artifact": null},
    "verdict": {
      "label": "LIKELY_AI|LIKELY_REAL|INCONCLUSIVE|ANALYSIS_FAILED",
      "risk": "low|moderate|high|unknown",
      "rationale": ["Primary fake probability 0.0044 <= 0.2"],
      "not_claimed": ["generator identity", "legal authenticity", "..."]
    },
    "error": null
  }
}
```

### Verdict Policy (Provisional Screening Thresholds)

| Fake Probability | Verdict | Risk |
|---|---|---|
| `>= 0.80` | `LIKELY_AI` | `high` |
| `<= 0.20` | `LIKELY_REAL` | `low` |
| `0.20 - 0.80` | `INCONCLUSIVE` | `moderate` |
| Detector error / no score | `ANALYSIS_FAILED` | `unknown` |

**These are provisional screening thresholds, not calibrated forensic certainty.**  
Detector errors never produce `LIKELY_REAL`. Missing metadata is not evidence of generation.

### Model Limitations

- Single model (CommunityForensics ViT-Small), not an ensemble
- Training data: 4,803 generators, but may not cover newest commercial models (Flux, Midjourney v7, etc.)
- Benchmark mean accuracy ~75%, but drops to ~35-42% on newest commercial generators
- No localization - output is image-level only
- No generator attribution

## Forensic Engine

The `/api/scans` endpoint runs four modular forensic analyzers alongside AI detection. Each analyzer produces a structured `Indicator` with computed result, interpretation, evidence category, limitations, and (where applicable) a visual artifact stored under `uploads/artifacts/{scan_id}/`.

### Implemented Analyzers

| ID | Name | Method | Evidence Category | Output Artifact |
|----|------|--------|-------------------|-----------------|
| `metadata` | Metadata Extraction | `computed` | `computed` | — |
| `ela` | Error Level Analysis (JPEG recompression at quality 90) | `computed` | `computed` | `ela.jpg` |
| `noise` | Noise Residual Statistics & Heatmap | `heuristic` | `heuristic` | `noise.jpg` |
| `frequency` | 2D FFT Magnitude Spectrum | `computed` | `computed` | `fft.jpg` |

### Analyzer Details

**Metadata Analyzer**
- Extracts format, dimensions, color mode, EXIF tags (if present), software, and timestamps
- Reports `has_exif`, `exif_tags_count`, software, datetime
- **Limitations**: Absence of EXIF is common and is NOT evidence of manipulation; metadata is easily stripped or forged

**Error Level Analysis (ELA)**
- Recompresses image as JPEG (quality 90) and computes absolute pixel-wise difference
- Scales difference for visualization; computes mean/max/std of difference
- **Limitations**: ELA is a heuristic; high-frequency textures naturally produce higher residuals; cannot independently prove forgery

**Noise Residual Analyzer**
- Estimates high-pass noise residuals via median filter subtraction
- Computes mean, standard deviation, max of noise residuals
- Generates noise heatmap artifact
- **Limitations**: Heuristic; influenced by texture, lighting, compression; not proof of editing

**Frequency Spectrum Analyzer**
- Computes 2D FFT magnitude spectrum (log scale), shifted to center
- Computes mean/std/max of log-magnitude spectrum
- Generates log-magnitude visualization artifact
- **Limitations**: Cannot identify specific generators; periodic patterns can arise from legitimate sources

### Analyzer Output Schema

Each indicator follows the schema:

```json
{
  "id": "metadata|ela|noise|frequency",
  "method": "computed|heuristic",
  "status": "ok|error|not_applicable",
  "value": {
    "result": { ... },
    "evidence_category": "computed|heuristic|verified|model_inference|unknown",
    "limitations": ["..."],
    "error": null
  },
  "note": "Human-readable interpretation string",
  "artifact": "uploads/artifacts/scan_id/ela.jpg"
}
```

### Forensic Limitations

- **No single analyzer proves authenticity or forgery** — each provides observational evidence
- **Absence of anomalies does not imply authenticity** — sophisticated forgeries may leave no detectable traces
- **Artifacts are visual aids only** — not calibrated quantitative evidence
- **ELA, noise, and frequency analyses are heuristic** — labeled as such in `method` and `evidence_category`

### Database Setup

### Start PostgreSQL

```bash
docker compose up -d
```

### Run Migrations

```bash
# Generate a new migration (after model changes)
.venv/bin/python -m alembic revision --autogenerate -m "description"

# Apply migrations
.venv/bin/python -m alembic upgrade head

# Check current revision
.venv/bin/python -m alembic current
```

### Environment Configuration

Copy `.env.example` to `.env` and adjust if needed:

```bash
cp .env.example .env
```

The default configuration uses:
- PostgreSQL: `postgresql+asyncpg://phantom:phantom@localhost:5432/phantom_phoenix`
- Database data persisted in Docker volume `postgres_data`

## Start the API server

```bash
.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Or with reload for development:

```bash
.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Service health and detector status |
| POST | `/api/scans` | Upload image for AI detection (multipart/form-data) |
| GET | `/api/scans` | Scan history (paginated, newest first) |
| GET | `/api/scans/{id}` | Get scan by ID (stored result, no re-inference) |

### POST `/api/scans` Request

- Multipart form field: `file`
- Allowed formats: JPEG, PNG, WEBP (validated by decode, not extension)
- Max size: 15 MiB
- Max dimensions: 8192 px per side

### POST `/api/scans` Response (201 Created)

```json
{
  "scan_id": "uuid",
  "status": "complete|failed",
  "result": {
    "scan_id": "uuid",
    "created_at": "ISO8601",
    "status": "complete|failed",
    "input": {
      "sha256": "hex",
      "filename": "original.jpg",
      "media_type": "image/jpeg",
      "byte_size": 12345,
      "width": 512,
      "height": 512
    },
    "models": [
      {
        "model_id": "buildborderless/CommunityForensics-DeepfakeDet-ViT",
        "model_revision": "...",
        "role": "primary",
        "status": "ok|error",
        "fake_probability": 0.0044,
        "raw_logit": -5.42,
        "threshold_policy": "0.80 likely_ai / 0.20 likely_real",
        "limitations": ["Not calibrated on images from this deployment", "..."],
        "device": "cuda|cpu",
        "duration_seconds": 0.19
      }
    ],
    "indicators": [
      {
        "id": "metadata",
        "method": "computed",
        "status": "ok",
        "value": {
          "result": {"format": "JPEG", "width": 512, "height": 512, "has_exif": false, ...},
          "evidence_category": "computed",
          "limitations": ["Absence of EXIF is common in web images..."],
          "error": null
        },
        "note": "Image format is JPEG (512x512, mode RGB). EXIF metadata is absent."
      },
      {
        "id": "ela",
        "method": "computed",
        "status": "ok",
        "value": {
          "result": {"mean_difference": 1.23, "max_difference": 45.0, "std_difference": 3.45},
          "evidence_category": "computed",
          "limitations": ["ELA is a heuristic visualization tool..."],
          "error": null
        },
        "note": "ELA mean difference is 1.23 (std 3.45). ...",
        "artifact": "uploads/artifacts/scan_id/ela.jpg"
      },
      {
        "id": "noise",
        "method": "heuristic",
        "status": "ok",
        "value": {
          "result": {"noise_std": 8.9, "noise_mean": -0.1, "noise_max": 42.3},
          "evidence_category": "heuristic",
          "limitations": ["Noise residuals are heuristic estimates..."],
          "error": null
        },
        "note": "Noise standard deviation is 8.90 (mean -0.10). ...",
        "artifact": "uploads/artifacts/scan_id/noise.jpg"
      },
      {
        "id": "frequency",
        "method": "computed",
        "status": "ok",
        "value": {
          "result": {"mean_magnitude": 24.5, "std_magnitude": 8.2, "max_magnitude": 65.3},
          "evidence_category": "computed",
          "limitations": ["Frequency domain analysis reveals spectral energy..."],
          "error": null
        },
        "note": "Frequency spectrum mean log-magnitude is 24.50 (std 8.20). ...",
        "artifact": "uploads/artifacts/scan_id/fft.jpg"
      }
    ],
    "explainability": {"status": "unavailable", "kind": null, "artifact": null},
    "verdict": {
      "label": "LIKELY_AI|LIKELY_REAL|INCONCLUSIVE|ANALYSIS_FAILED",
      "risk": "low|moderate|high|unknown",
      "rationale": ["Primary fake probability 0.0044 <= 0.2"],
      "not_claimed": ["generator identity", "legal authenticity", "..."]
    },
    "error": null
  }
}
```

### Verdict Policy (Provisional Screening Thresholds)

| Fake Probability | Verdict | Risk |
|---|---|---|
| `>= 0.80` | `LIKELY_AI` | `high` |
| `<= 0.20` | `LIKELY_REAL` | `low` |
| `0.20 - 0.80` | `INCONCLUSIVE` | `moderate` |
| Detector error / no score | `ANALYSIS_FAILED` | `unknown` |

**These are provisional screening thresholds, not calibrated forensic certainty.**  
Detector errors never produce `LIKELY_REAL`. Missing metadata is not evidence of generation.

### Model Limitations

- Single model (CommunityForensics ViT-Small), not an ensemble
- Training data: 4,803 generators, but may not cover newest commercial models (Flux, Midjourney v7, etc.)
- Benchmark mean accuracy ~75%, but drops to ~35-42% on newest commercial generators
- No localization - output is image-level only
- No generator attribution

## Run Tests

```bash
# Unit tests (mocked detector, no GPU/model download)
.venv/bin/python -m pytest tests/ -v -k "not test_database"

# Real model smoke test (downloads ~83 MB weights, requires GPU or CPU)
RUN_REAL_MODEL=1 .venv/bin/python -m pytest tests/test_real_model_smoke.py -v

# Database integration tests (requires PostgreSQL)
RUN_DB_TESTS=1 .venv/bin/python -m pytest tests/test_database.py -v
```

### Test Notes

- **Unit tests**: 28 tests passing, mocked detector, no GPU/download required
- **Forensic tests**: 6 tests passing (metadata, ELA, noise, frequency, runner integration)
- **Real model smoke test**: Passes on RTX 3050 (4GB), CUDA inference ~190ms + forensics ~150ms
- **Database integration tests**: Some flakiness due to async event loop/connection pool interactions; core functionality verified manually. See `tests/test_database.py` for details.

## If CUDA fails

Record the JSON error. Re-run with `--device cpu` only to confirm the model itself loads. Do not change the model id. Lowest-risk alternative if this checkpoint cannot load at all: stop and report the blocker. The next candidate, not yet installed, is `dima806/ai_vs_real_image_detection` (Apache-2.0 ViT, two-class softmax, older CIFAKE training). It must not be swapped in silently, and its logit layout is different.