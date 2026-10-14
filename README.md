# PHANTOM PHOENIX

Image authenticity and digital forensic intelligence platform.

## Quick Start

### Prerequisites
- uv (fast Python package manager)
- NVIDIA GPU with driver (for CUDA inference) or CPU fallback
- Docker & Docker Compose (for PostgreSQL)

### Environment Setup

```bash
# Create isolated Python 3.12 environment
uv venv --python 3.12 .venv

# Install PyTorch with CUDA 12.8
uv pip install --python .venv/bin/python \
  torch==2.11.0+cu128 torchvision==0.26.0+cu128 \
  --index-url https://download.pytorch.org/whl/cu128

# Install ML dependencies
uv pip install --python .venv/bin/python -r requirements-ml.txt

# Install API dependencies
uv pip install --python .venv/bin/python -r requirements-api.txt
```

### Database Setup

```bash
# Start PostgreSQL
docker compose up -d

# Run migrations
.venv/bin/python -m alembic upgrade head
```

### Start API Server

```bash
# Development (with auto-reload)
.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Production
.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Service health and detector status |
| POST | `/api/scans` | Upload image for AI detection & forensics (multipart/form-data) |
| GET | `/api/scans` | Paginated scan history |
| GET | `/api/scans/{id}` | Retrieve stored scan result & forensic indicators |

### Example Usage

```bash
# Health check
curl http://localhost:8000/api/health

# Analyze image (runs AI detection + metadata, ELA, noise, frequency analyzers)
curl -X POST http://localhost:8000/api/scans \
  -F "file=@/path/to/image.jpg"

# Get scan history
curl "http://localhost:8000/api/scans?limit=10"
```

### Run Tests

```bash
# Unit tests (mocked detector, forensics engine, no GPU required)
.venv/bin/python -m pytest tests/ -v -k "not test_database"

# Real model smoke test (downloads ~83 MB weights, requires GPU or CPU)
RUN_REAL_MODEL=1 .venv/bin/python -m pytest tests/test_real_model_smoke.py -v

# Database integration tests (requires PostgreSQL)
RUN_DB_TESTS=1 .venv/bin/python -m pytest tests/test_database.py -v
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   FastAPI   │────▶│  Detector   │
│  (Upload)   │     │   Backend   │     │  Adapter    │
└─────────────┘     └──────┬──────┘     └──────┬──────┘
                           │                   │
                    ┌──────▼──────┐     ┌──────▼──────┐
                    │ PostgreSQL  │     │  Forensics  │
                    │  (Scans)    │     │  Analyzers  │
                    └─────────────┘     └─────────────┘
```

### Components

- **FastAPI Backend**: REST API with validated upload, health checks, scan persistence
- **Detector Adapter**: Singleton wrapper for CommunityForensics ViT-Small model with CUDA/CPU fallback
- **Forensics Engine**: Modular analyzers (Metadata, Error Level Analysis, Noise Residual, Frequency Spectrum) producing structured indicators and visual artifacts (`ela.jpg`, `noise.jpg`, `fft.jpg`)
- **PostgreSQL**: Persistent storage for scan history and results (JSONB)
- **SQLAlchemy + Alembic**: ORM and migrations

## Forensic Analyzers

1. **Metadata Analyzer (`metadata`)**: Extracts image format, dimensions, color mode, EXIF tags, software, and timestamps.
2. **Error Level Analysis (`ela`)**: Recompresses image as JPEG (quality 90) and compares residuals to highlight compression inconsistencies.
3. **Noise Residual Analyzer (`noise`)**: Estimates high-pass noise residuals and computes spatial noise variance statistics.
4. **Frequency Spectrum Analyzer (`frequency`)**: Computes 2D Fast Fourier Transform (FFT) magnitude spectrum and spectral statistics.

## Model Limitations

- **Single model**: CommunityForensics ViT-Small (21.8M params), not an ensemble
- **Training data**: 4,803 generators, but may not cover newest commercial models (Flux, Midjourney v7, etc.)
- **Benchmark accuracy**: ~75% mean, but drops to ~35-42% on newest commercial generators
- **No localization**: Image-level only, no pixel-level forgery maps
- **No generator attribution**: Output is binary (AI vs real) probability
- **Provisional thresholds**: 0.80/0.20 are screening thresholds, not calibrated forensic certainty

## Verdict Policy

| Fake Probability | Verdict | Risk |
|------------------|---------|------|
| ≥ 0.80 | `LIKELY_AI` | `high` |
| ≤ 0.20 | `LIKELY_REAL` | `low` |
| 0.20 - 0.80 | `INCONCLUSIVE` | `moderate` |
| Detector error | `ANALYSIS_FAILED` | `unknown` |

**These are provisional screening thresholds, not calibrated forensic certainty.**  
Detector errors never produce `LIKELY_REAL`. Missing metadata is not evidence of generation.

## Security

- File validation by decode (not extension/MIME)
- Max 15 MiB, 8192 px per side
- SHA-256 content addressing
- UUID scan IDs (no client filenames on disk)
- Controlled local artifact storage (`uploads/artifacts/{scan_id}/`)
- CORS restricted to dev origins
- No secrets in repository (use `.env`)

## License

MIT License - see LICENSE file.