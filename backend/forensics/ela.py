"""Error Level Analysis (ELA) forensic analyzer."""

from __future__ import annotations

import io
import numpy as np
from PIL import Image, ImageChops, ImageEnhance

from backend.forensics import ForensicAnalyzer, ForensicContext, ForensicResult


class ElaAnalyzer(ForensicAnalyzer):
    """Performs Error Level Analysis (ELA) via JPEG recompression comparison."""

    @property
    def analyzer_id(self) -> str:
        return "ela"

    def analyze(self, context: ForensicContext) -> ForensicResult:
        try:
            original = context.pil_image.copy()
            width, height = original.size

            # Recompress image in memory as JPEG at quality 90
            buffer = io.BytesIO()
            original.save(buffer, "JPEG", quality=90)
            buffer.seek(0)
            recompressed = Image.open(buffer)
            recompressed.load()

            # Compute difference between original and recompressed
            # ELA = abs(original - recompressed)
            diff = ImageChops.difference(original, recompressed)

            # Enhance difference to make subtle compression variations visible
            extrema = diff.getextrema()
            max_diff = max([ex[1] for ex in extrema]) if extrema else 1
            if max_diff == 0:
                max_diff = 1
            scale = 255.0 / max_diff

            enhancer = ImageEnhance.Brightness(diff)
            ela_image = enhancer.enhance(scale)

            # Compute statistical metrics on diff
            diff_arr = np.array(diff, dtype=np.float32)
            mean_diff = float(np.mean(diff_arr))
            max_diff_val = float(np.max(diff_arr))
            std_diff = float(np.std(diff_arr))

            # Save artifact
            artifact_rel_path = self._save_artifact(context.scan_id, "ela.jpg", ela_image)

            format_note = (
                f"Source format was {original.format}. ELA performed via JPEG recompression at quality 90."
                if original.format != "JPEG"
                else "ELA performed via JPEG recompression at quality 90."
            )

            result_dict = {
                "quality_factor": 90,
                "mean_difference": round(mean_diff, 4),
                "max_difference": round(max_diff_val, 4),
                "std_difference": round(std_diff, 4),
            }

            interpretation = (
                f"ELA mean difference is {mean_diff:.2f} (std {std_diff:.2f}). "
                "Uniform compression error levels suggest homogeneous processing, "
                "while localized high-contrast error variations can indicate splicing or local editing."
            )

            return ForensicResult(
                id=self.analyzer_id,
                status="ok",
                method="computed",
                result=result_dict,
                interpretation=interpretation,
                evidence_category="computed",
                limitations=[
                    format_note,
                    "ELA is a heuristic visualization tool and cannot independently establish authenticity or prove forgery.",
                    "High-frequency textures, text, and sharp edges naturally produce higher compression residuals.",
                ],
                artifact=artifact_rel_path,
                error=None,
            )

        except Exception as exc:
            return self._create_error_result(str(exc))