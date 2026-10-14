"""Noise residual forensic analyzer."""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from backend.forensics import ForensicAnalyzer, ForensicContext, ForensicResult


class NoiseAnalyzer(ForensicAnalyzer):
    """Calculates noise-residual statistics and generates noise map visualization."""

    @property
    def analyzer_id(self) -> str:
        return "noise"

    def analyze(self, context: ForensicContext) -> ForensicResult:
        try:
            img = context.pil_image.convert("L")  # Grayscale
            img_arr = np.array(img, dtype=np.float32)

            # Extract noise residual using a median filter subtraction (high-pass noise estimation)
            filtered = img.filter(ImageFilter.MedianFilter(size=3))
            filtered_arr = np.array(filtered.convert("L"), dtype=np.float32)

            noise_residual = img_arr - filtered_arr

            # Compute statistics
            mean_noise = float(np.mean(noise_residual))
            std_noise = float(np.std(noise_residual))
            max_noise = float(np.max(np.abs(noise_residual)))

            # Generate noise visualization map
            # Normalize noise residual to 0-255
            normalized = np.abs(noise_residual)
            if normalized.max() > 0:
                normalized = (normalized / normalized.max()) * 255.0
            noise_img = Image.fromarray(normalized.astype(np.uint8)).convert("RGB")

            # Save artifact
            artifact_rel_path = self._save_artifact(context.scan_id, "noise.jpg", noise_img)

            result_dict = {
                "noise_mean": round(mean_noise, 4),
                "noise_std": round(std_noise, 4),
                "noise_max": round(max_noise, 4),
            }

            interpretation = (
                f"Noise standard deviation is {std_noise:.2f} (mean {mean_noise:.2f}). "
                "Uniform noise distribution across spatial regions suggests consistent acquisition, "
                "whereas abrupt localized noise variance changes can indicate tampering."
            )

            return ForensicResult(
                id=self.analyzer_id,
                status="ok",
                method="heuristic",
                result=result_dict,
                interpretation=interpretation,
                evidence_category="heuristic",
                limitations=[
                    "Noise residuals are heuristic estimates and are heavily influenced by image texture, lighting, and compression.",
                    "AI-generated images often exhibit distinct noise patterns due to diffusion upsampling, but noise consistency alone is not proof of authenticity.",
                ],
                artifact=artifact_rel_path,
                error=None,
            )

        except Exception as exc:
            return self._create_error_result(str(exc))