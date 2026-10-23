"""Frequency domain (2D FFT) forensic analyzer."""

from __future__ import annotations

import numpy as np
from PIL import Image

from backend.forensics import ForensicAnalyzer, ForensicContext, ForensicResult


class FrequencyAnalyzer(ForensicAnalyzer):
    """Computes 2D FFT magnitude spectrum and frequency statistics."""

    @property
    def analyzer_id(self) -> str:
        return "frequency"

    def analyze(self, context: ForensicContext) -> ForensicResult:
        try:
            img = context.pil_image.convert("L")
            img_arr = np.array(img, dtype=np.float32)

            # Compute 2D FFT and shift zero-frequency component to center
            f_transform = np.fft.fft2(img_arr)
            f_shift = np.fft.fftshift(f_transform)

            # Magnitude spectrum (log scale for visualization)
            magnitude_spectrum = 20 * np.log(np.abs(f_shift) + 1e-5)

            # Compute basic frequency statistics
            mean_magnitude = float(np.mean(magnitude_spectrum))
            std_magnitude = float(np.std(magnitude_spectrum))
            max_magnitude = float(np.max(magnitude_spectrum))

            # Normalize for visualization
            norm_spectrum = magnitude_spectrum - magnitude_spectrum.min()
            if norm_spectrum.max() > 0:
                norm_spectrum = (norm_spectrum / norm_spectrum.max()) * 255.0
            fft_img = Image.fromarray(norm_spectrum.astype(np.uint8)).convert("RGB")

            # Save artifact
            artifact_rel_path = self._save_artifact(context.scan_id, "fft.jpg", fft_img)

            result_dict = {
                "mean_magnitude": round(mean_magnitude, 4),
                "std_magnitude": round(std_magnitude, 4),
                "max_magnitude": round(max_magnitude, 4),
            }

            interpretation = (
                f"Frequency spectrum mean log-magnitude is {mean_magnitude:.2f} (std {std_magnitude:.2f}). "
                "Periodic grid artifacts or high-frequency spectral suppression can sometimes be observed "
                "in certain generative upsampling architectures."
            )

            return ForensicResult(
                id=self.analyzer_id,
                status="ok",
                method="computed",
                result=result_dict,
                interpretation=interpretation,
                evidence_category="computed",
                limitations=[
                    "Frequency domain analysis reveals spectral energy distribution but CANNOT identify specific generators or prove authenticity.",
                    "Strong periodic patterns can arise from legitimate sources such as scanner grids, screens, or regular textures.",
                ],
                artifact=artifact_rel_path,
                error=None,
            )

        except Exception as exc:
            return self._create_error_result(str(exc))