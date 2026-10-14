"""Image validation and processing utilities."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from PIL import Image

from backend.config import settings


@dataclass(frozen=True)
class ValidatedImage:
    """Validated and decoded image with metadata."""

    pil_image: Image.Image
    sha256: str
    byte_size: int
    width: int
    height: int
    media_type: str
    original_filename: str


class ImageValidationError(Exception):
    """Raised when image validation fails."""

    def __init__(self, code: str, message: str, detail: str | None = None) -> None:
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(message)


ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MIME_TO_FORMAT = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}


def validate_and_decode(file: BinaryIO, filename: str, content_type: str | None) -> ValidatedImage:
    """
    Validate and decode an uploaded image.

    Validates by actual decode, not by extension or MIME type.
    Enforces size and dimension limits.
    Returns validated image with SHA-256 and metadata.
    """
    # Read entire file into memory for validation (max 15MB)
    max_bytes = settings.max_image_size_mb * 1024 * 1024
    data = file.read(max_bytes + 1)

    if len(data) > max_bytes:
        raise ImageValidationError(
            code="FILE_TOO_LARGE",
            message=f"File exceeds maximum size of {settings.max_image_size_mb} MiB",
            detail=f"Received {len(data)} bytes, limit is {max_bytes} bytes",
        )

    if len(data) == 0:
        raise ImageValidationError(
            code="EMPTY_FILE",
            message="Uploaded file is empty",
        )

    # Calculate SHA-256
    sha256 = hashlib.sha256(data).hexdigest()

    # Decode and validate image
    try:
        pil_image = Image.open(io.BytesIO(data))
        pil_image.load()  # Force decode to catch truncation/corruption
        fmt = pil_image.format
    except Exception as exc:
        raise ImageValidationError(
            code="INVALID_IMAGE",
            message="File is not a valid image or is corrupted",
            detail=str(exc),
        )

    if fmt not in ALLOWED_FORMATS:
        raise ImageValidationError(
            code="UNSUPPORTED_FORMAT",
            message=f"Unsupported image format: {fmt}. Allowed: {', '.join(sorted(ALLOWED_FORMATS))}",
            detail=f"Detected format: {fmt}",
        )

    # Convert to RGB for model compatibility
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")

    width, height = pil_image.size

    if width > settings.max_dimension_px or height > settings.max_dimension_px:
        raise ImageValidationError(
            code="DIMENSIONS_TOO_LARGE",
            message=f"Image dimensions exceed maximum of {settings.max_dimension_px} pixels per side",
            detail=f"Received {width}x{height}",
        )

    if width == 0 or height == 0:
        raise ImageValidationError(
            code="ZERO_DIMENSION",
            message="Image has zero width or height",
        )

    # Determine media type from actual format
    media_type = next(
        (mt for mt, f in MIME_TO_FORMAT.items() if f == fmt),
        "application/octet-stream",
    )

    return ValidatedImage(
        pil_image=pil_image,
        sha256=sha256,
        byte_size=len(data),
        width=width,
        height=height,
        media_type=media_type,
        original_filename=filename,
    )


def save_image(data: bytes, scan_id: str, upload_dir: Path) -> Path:
    """Save raw image bytes to upload directory with UUID filename."""
    upload_dir.mkdir(parents=True, exist_ok=True)
    # Use scan_id as filename, preserve extension hint from original if safe
    dest = upload_dir / scan_id
    dest.write_bytes(data)
    return dest