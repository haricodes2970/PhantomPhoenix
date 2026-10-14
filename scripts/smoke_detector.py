"""Smoke-test the provisional Community Forensics image detector.

Reports environment facts and one real forward pass. Does not claim accuracy.
Exits 0 when inference completes, 2 when no test image was supplied, 1 on any
other blocker. Never substitutes a different model.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

MODEL_ID = "buildborderless/CommunityForensics-DeepfakeDet-ViT"
# Documented semantics for THIS checkpoint only. Do not reuse for other models.
# config.json: num_labels == 1. preprocessor_config.json: CLIP mean/std,
# shortest_edge 440, center crop 384. Card: sigmoid(logit) is P(fake).
EXPECTED_NUM_LABELS = 1
EXPECTED_SHORTEST_EDGE = 440
EXPECTED_CROP = 384


def emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def fail(payload: dict[str, object], code: int) -> None:
    payload["status"] = "blocked"
    emit(payload)
    raise SystemExit(code)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--image",
        type=Path,
        help="Local image file. Required for inference. Not downloaded.",
    )
    parser.add_argument(
        "--device",
        choices=("auto", "cuda", "cpu"),
        default="auto",
        help="auto tries CUDA, then CPU if CUDA is unavailable or the forward pass fails.",
    )
    args = parser.parse_args()

    report: dict[str, object] = {
        "model_id": MODEL_ID,
        "accuracy_claim": None,
        "note": "Smoke test only. A single forward pass is not an accuracy measurement.",
    }

    report["python"] = sys.version
    try:
        import torch
    except Exception as exc:
        report["blocker"] = f"torch import failed: {exc}"
        fail(report, 1)

    try:
        import transformers
    except Exception as exc:
        report["blocker"] = f"transformers import failed: {exc}"
        fail(report, 1)

    report["torch"] = torch.__version__
    report["transformers"] = transformers.__version__
    report["cuda_available"] = bool(torch.cuda.is_available())
    report["cuda_device_count"] = int(torch.cuda.device_count())
    if torch.cuda.is_available():
        report["gpu_name"] = torch.cuda.get_device_name(0)
    else:
        report["gpu_name"] = None

    if args.image is None:
        report["blocker"] = "No test image supplied. Pass --image PATH. No prediction was invented."
        report["inference"] = None
        fail(report, 2)

    image_path = args.image.expanduser().resolve()
    if not image_path.is_file():
        report["blocker"] = f"Test image not found: {image_path}"
        fail(report, 2)

    try:
        from PIL import Image
        from transformers import ViTForImageClassification, ViTImageProcessor
    except Exception as exc:
        report["blocker"] = f"import failed: {exc}"
        fail(report, 1)

    try:
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            report["input_image"] = {
                "path": str(image_path),
                "width": image.width,
                "height": image.height,
                "mode_after_convert": image.mode,
            }
            pixels = image.copy()
    except Exception as exc:
        report["blocker"] = f"Could not decode image: {exc}"
        fail(report, 1)

    try:
        processor = ViTImageProcessor.from_pretrained(MODEL_ID)
        model = ViTForImageClassification.from_pretrained(MODEL_ID)
    except Exception as exc:
        report["blocker"] = (
            "Could not load the candidate model. No substitute was attempted. "
            f"{type(exc).__name__}: {exc}"
        )
        report["traceback"] = traceback.format_exc()
        fail(report, 1)

    config = model.config
    size = getattr(processor, "size", None)
    crop = getattr(processor, "crop_size", None)
    # transformers 5.x uses SizeDict objects. Access attributes, not dict keys.
    shortest = getattr(size, "shortest_edge", None)
    crop_edge = getattr(crop, "height", None) or getattr(crop, "shortest_edge", None)
    num_labels = int(getattr(config, "num_labels", -1))
    report["model_revision"] = str(getattr(model, "name_or_path", MODEL_ID))
    report["model_config"] = {
        "num_labels": num_labels,
        "num_attention_heads": int(getattr(config, "num_attention_heads", -1)),
        "image_size": int(getattr(config, "image_size", -1)),
        "id2label": {str(k): str(v) for k, v in dict(getattr(config, "id2label", {})).items()},
        "problem_type": getattr(config, "problem_type", None),
    }
    report["preprocessor"] = {
        "size_shortest_edge": shortest,
        "crop_height": getattr(crop, "height", None),
        "crop_width": getattr(crop, "width", None),
        "do_center_crop": bool(getattr(processor, "do_center_crop", False)),
        "image_mean": list(getattr(processor, "image_mean", []) or []),
        "image_std": list(getattr(processor, "image_std", []) or []),
    }
    semantics_ok = (
        num_labels == EXPECTED_NUM_LABELS
        and shortest == EXPECTED_SHORTEST_EDGE
        and crop_edge == EXPECTED_CROP
    )
    report["documented_semantics_match"] = semantics_ok
    if not semantics_ok:
        report["blocker"] = (
            "Loaded checkpoint does not match documented preprocessing/output semantics "
            f"(expected num_labels={EXPECTED_NUM_LABELS}, shortest_edge="
            f"{EXPECTED_SHORTEST_EDGE}, crop={EXPECTED_CROP}; "
            f"got num_labels={num_labels}, shortest_edge={shortest}, crop={crop_edge}). "
            "Inference was not run. No substitute model was loaded."
        )
        fail(report, 1)

    # This checkpoint: one logit, sigmoid = fake probability. Not a softmax pair.
    report["output_semantics"] = (
        "num_labels=1. raw_output is the single logit. "
        "fake_probability = sigmoid(logit), per the model card. "
        "This mapping is specific to CommunityForensics-DeepfakeDet-ViT."
    )

    def run_on(device_name: str) -> dict[str, object]:
        device = torch.device(device_name)
        model.to(device)
        model.eval()
        inputs = processor(images=pixels, return_tensors="pt")
        inputs = {key: value.to(device) for key, value in inputs.items()}
        if device.type == "cuda":
            torch.cuda.synchronize()
        started = time.perf_counter()
        with torch.inference_mode():
            logits = model(**inputs).logits
        if device.type == "cuda":
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - started
        logit = float(logits.detach().float().cpu().reshape(-1)[0])
        fake_probability = float(torch.sigmoid(torch.tensor(logit)))
        return {
            "device": device_name,
            "pixel_values_shape": list(inputs["pixel_values"].shape),
            "logits_shape": list(logits.shape),
            "raw_logit": logit,
            "fake_probability": fake_probability,
            "duration_seconds": round(elapsed, 6),
        }

    attempted: list[str] = []
    errors: list[str] = []
    if args.device == "cpu":
        order = ["cpu"]
    elif args.device == "cuda":
        order = ["cuda"]
    else:
        order = ["cuda", "cpu"] if torch.cuda.is_available() else ["cpu"]

    inference: dict[str, object] | None = None
    for device_name in order:
        if device_name == "cuda" and not torch.cuda.is_available():
            errors.append("cuda requested but torch.cuda.is_available() is false")
            continue
        attempted.append(device_name)
        try:
            inference = run_on(device_name)
            break
        except Exception as exc:
            errors.append(f"{device_name}: {type(exc).__name__}: {exc}")

    report["devices_attempted"] = attempted
    report["device_errors"] = errors
    if inference is None:
        report["blocker"] = "Inference failed on every attempted device. No substitute model was loaded."
        report["traceback"] = traceback.format_exc()
        fail(report, 1)

    report["inference"] = inference
    report["status"] = "ok"
    if inference["device"] == "cpu" and "cuda" in errors[0] if errors else False:
        report["execution"] = "cpu_fallback"
    elif inference["device"] == "cpu" and any(item.startswith("cuda:") for item in errors):
        report["execution"] = "cpu_after_cuda_failure"
    else:
        report["execution"] = str(inference["device"])
    emit(report)


if __name__ == "__main__":
    main()
