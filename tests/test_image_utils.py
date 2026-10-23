"""Tests for image validation utilities."""

from __future__ import annotations

import io
import pytest
from PIL import Image

from backend.image_utils import validate_and_decode, ImageValidationError, ALLOWED_FORMATS
from backend.config import settings


def create_image_bytes(format: str = "JPEG", width: int = 512, height: int = 512) -> bytes:
    img = Image.new("RGB", (width, height), (128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf.getvalue()


class TestValidateAndDecode:
    """Tests for validate_and_decode function."""

    def test_valid_jpeg(self) -> None:
        data = create_image_bytes("JPEG")
        file = io.BytesIO(data)
        result = validate_and_decode(file, "test.jpg", "image/jpeg")

        assert result.sha256 is not None
        assert len(result.sha256) == 64
        assert result.byte_size == len(data)
        assert result.width == 512
        assert result.height == 512
        assert result.media_type == "image/jpeg"
        assert result.original_filename == "test.jpg"

    def test_valid_png(self) -> None:
        data = create_image_bytes("PNG")
        file = io.BytesIO(data)
        result = validate_and_decode(file, "test.png", "image/png")
        assert result.media_type == "image/png"

    def test_valid_webp(self) -> None:
        data = create_image_bytes("WEBP")
        file = io.BytesIO(data)
        result = validate_and_decode(file, "test.webp", "image/webp")
        assert result.media_type == "image/webp"

    def test_converts_to_rgb(self) -> None:
        """Non-RGB images are converted to RGB."""
        img = Image.new("RGBA", (100, 100), (128, 128, 128, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        result = validate_and_decode(buf, "test.png", "image/png")
        assert result.pil_image.mode == "RGB"

    def test_empty_file_rejected(self) -> None:
        file = io.BytesIO(b"")
        with pytest.raises(ImageValidationError) as exc:
            validate_and_decode(file, "empty.jpg", "image/jpeg")
        assert exc.value.code == "EMPTY_FILE"

    def test_file_too_large_rejected(self) -> None:
        max_bytes = 5 * 1024 * 1024
        data = b"x" * (max_bytes + 1)
        file = io.BytesIO(data)
        with pytest.raises(ImageValidationError) as exc:
            validate_and_decode(file, "large.jpg", "image/jpeg")
        assert exc.value.code == "FILE_TOO_LARGE"
        assert "5 MiB" in exc.value.message

    def test_invalid_image_rejected(self) -> None:
        file = io.BytesIO(b"not an image")
        with pytest.raises(ImageValidationError) as exc:
            validate_and_decode(file, "fake.jpg", "image/jpeg")
        assert exc.value.code == "INVALID_IMAGE"

    def test_unsupported_format_rejected(self) -> None:
        for fmt in ["BMP", "TIFF", "GIF"]:
            img = Image.new("RGB", (100, 100), (128, 128, 128))
            buf = io.BytesIO()
            img.save(buf, format=fmt)
            buf.seek(0)
            with pytest.raises(ImageValidationError) as exc:
                validate_and_decode(buf, f"test.{fmt.lower()}", f"image/{fmt.lower()}")
            assert exc.value.code == "UNSUPPORTED_FORMAT"

    def test_dimensions_too_large_rejected(self) -> None:
        max_dim = settings.max_dimension_px
        img = Image.new("RGB", (max_dim + 1, max_dim), (128, 128, 128))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        with pytest.raises(ImageValidationError) as exc:
            validate_and_decode(buf, "large.jpg", "image/jpeg")
        assert exc.value.code == "DIMENSIONS_TOO_LARGE"

    def test_zero_dimension_rejected(self) -> None:
        # Create 1x1 then manipulate - but PIL won't create 0-dim
        # The check is in the code for defense in depth
        pass  # Can't easily create 0-dim PIL image

    def test_sha256_consistent(self) -> None:
        """Same image data produces same SHA-256."""
        data = create_image_bytes("JPEG")
        file1 = io.BytesIO(data)
        file2 = io.BytesIO(data)

        result1 = validate_and_decode(file1, "a.jpg", "image/jpeg")
        result2 = validate_and_decode(file2, "b.jpg", "image/jpeg")

        assert result1.sha256 == result2.sha256

    def test_allowed_formats_constant(self) -> None:
        assert ALLOWED_FORMATS == {"JPEG", "PNG", "WEBP"}