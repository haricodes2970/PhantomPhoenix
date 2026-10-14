"""Metadata forensic analyzer."""

from __future__ import annotations

from PIL import Image
from PIL.ExifTags import TAGS

from backend.forensics import ForensicAnalyzer, ForensicContext, ForensicResult


class MetadataAnalyzer(ForensicAnalyzer):
    """Extracts format, dimensions, color mode, EXIF, and XMP metadata."""

    @property
    def analyzer_id(self) -> str:
        return "metadata"

    def analyze(self, context: ForensicContext) -> ForensicResult:
        try:
            img = context.pil_image
            format_name = img.format or context.media_type.split("/")[-1].upper() if context.media_type else "UNKNOWN"
            mode = img.mode
            width, height = img.size

            # Extract EXIF if present
            exif_data: dict[str, str] = {}
            raw_exif = img.getexif()
            if raw_exif:
                for tag_id, value in raw_exif.items():
                    tag_name = TAGS.get(tag_id, str(tag_id))
                    # Convert bytes/non-string values safely
                    if isinstance(value, bytes):
                        try:
                            value = value.decode("utf-8", errors="ignore")
                        except Exception:
                            value = str(value)
                    elif not isinstance(value, (str, int, float)):
                        value = str(value)
                    exif_data[tag_name] = value

            # Extract XMP / info dict if available in PIL info
            info_data: dict[str, str] = {}
            for k, v in img.info.items():
                if k in ("xmp", "XML:com.adobe.xmp"):
                    info_data["xmp_present"] = "True"
                elif isinstance(v, (str, int, float)):
                    info_data[str(k)] = str(v)

            software = exif_data.get("Software") or info_data.get("software")
            datetime_str = exif_data.get("DateTime") or exif_data.get("DateTimeOriginal")

            has_exif = len(exif_data) > 0
            exif_status = "present" if has_exif else "absent"

            result_dict = {
                "format": format_name,
                "mode": mode,
                "width": width,
                "height": height,
                "has_exif": has_exif,
                "exif_tags_count": len(exif_data),
                "software": software,
                "datetime": datetime_str,
                "exif_sample": {k: v for k, v in list(exif_data.items())[:15]},
                "info_tags": info_data,
            }

            interpretation = (
                f"Image format is {format_name} ({width}x{height}, mode {mode}). "
                f"EXIF metadata is {exif_status}."
            )
            if software:
                interpretation += f" Recorded software: {software}."

            return ForensicResult(
                id=self.analyzer_id,
                status="ok",
                method="computed",
                result=result_dict,
                interpretation=interpretation,
                evidence_category="computed",
                limitations=[
                    "Absence of EXIF or metadata is common in web images and is NOT evidence of AI generation or tampering.",
                    "Metadata timestamps and software tags can be easily stripped or forged.",
                ],
                artifact=None,
                error=None,
            )

        except Exception as exc:
            return self._create_error_result(str(exc))