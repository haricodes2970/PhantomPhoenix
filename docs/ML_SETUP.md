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
```

`.venv/` and the Hugging Face weight cache are gitignored. Weights download on the first smoke test into the default Hugging Face cache (`~/.cache/huggingface`), which is outside this repo.

## Smoke test

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

## If CUDA fails

Record the JSON error. Re-run with `--device cpu` only to confirm the model itself loads. Do not change the model id. Lowest-risk alternative if this checkpoint cannot load at all: stop and report the blocker. The next candidate, not yet installed, is `dima806/ai_vs_real_image_detection` (Apache-2.0 ViT, two-class softmax, older CIFAKE training). It must not be swapped in silently, and its logit layout is different.
