"""Tests for the image forensics engine analyzers."""

from __future__ import annotations

import io
import pytest
from PIL import Image

from backend.forensics import ForensicContext
from backend.forensics.metadata import MetadataAnalyzer
from backend.forensics.ela import ElaAnalyzer
from backend.forensics.noise import NoiseAnalyzer
from backend.forensics.frequency import FrequencyAnalyzer
from backend.forensics.runner import run_all_analyzers
from backend.image_utils import ValidatedImage


def create_test_image(format: str = "JPEG", width: int = 128, height: int = 128) -> ValidatedImage:
    """Helper to create a ValidatedImage for testing."""
    img = Image.new("RGB", (width, height), (100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    data = buf.getvalue()
    
    return ValidatedImage(
        pil_image=img,
        sha256="dummy_sha256",
        byte_size=len(data),
        width=width,
        height=height,
        media_type=f"image/{format.lower()}",
        original_filename=f"test.{format.lower()}",
    )


def test_metadata_analyzer() -> None:
    """Test metadata extraction analyzer."""
    val_img = create_test_image("JPEG")
    context = ForensicContext(
        pil_image=val_img.pil_image,
        image_bytes=b"",
        sha256=val_img.sha256,
        scan_id="test-scan-uuid",
        media_type=val_img.media_type,
        width=val_img.width,
        height=val_img.height,
        original_filename=val_img.original_filename,
    )

    analyzer = MetadataAnalyzer()
    result = analyzer.analyze(context)

    assert result.status == "ok"
    assert result.id == "metadata"
    assert result.result["format"] == "JPEG"
    assert result.result["width"] == 128
    assert result.result["height"] == 128
    assert "EXIF" in result.interpretation or "format" in result.interpretation


def test_ela_analyzer_jpeg() -> None:
    """Test ELA analyzer on JPEG image."""
    val_img = create_test_image("JPEG")
    context = ForensicContext(
        pil_image=val_img.pil_image,
        image_bytes=b"",
        sha256=val_img.sha256,
        scan_id="test-scan-uuid",
        media_type=val_img.media_type,
        width=val_img.width,
        height=val_img.height,
        original_filename=val_img.original_filename,
    )

    analyzer = ElaAnalyzer()
    result = analyzer.analyze(context)

    assert result.status == "ok"
    assert result.id == "ela"
    assert "mean_difference" in result.result
    assert result.artifact is not None
    assert "ela.jpg" in result.artifact


def test_ela_analyzer_png() -> None:
    """Test ELA analyzer on PNG image (handles lossy comparison)."""
    val_img = create_test_image("PNG")
    context = ForensicContext(
        pil_image=val_img.pil_image,
        image_bytes=b"",
        sha256=val_img.sha256,
        scan_id="test-scan-uuid",
        media_type=val_img.media_type,
        width=val_img.width,
        height=val_img.height,
        original_filename=val_img.original_filename,
    )

    analyzer = ElaAnalyzer()
    result = analyzer.analyze(context)

    assert result.status == "ok"
    assert result.id == "ela"
    assert result.artifact is not None


def test_noise_analyzer() -> None:
    """Test noise residual analyzer."""
    val_img = create_test_image("JPEG")
    context = ForensicContext(
        pil_image=val_img.pil_image,
        image_bytes=b"",
        sha256=val_img.sha256,
        scan_id="test-scan-uuid",
        media_type=val_img.media_type,
        width=val_img.width,
        height=val_img.height,
        original_filename=val_img.original_filename,
    )

    analyzer = NoiseAnalyzer()
    result = analyzer.analyze(context)

    assert result.status == "ok"
    assert result.id == "noise"
    assert "noise_std" in result.result
    assert result.artifact is not None
    assert "noise.jpg" in result.artifact


def test_frequency_analyzer() -> None:
    """Test 2D FFT frequency domain analyzer."""
    val_img = create_test_image("JPEG")
    context = ForensicContext(
        pil_image=val_img.pil_image,
        image_bytes=b"",
        sha256=val_img.sha256,
        scan_id="test-scan-uuid",
        media_type=val_img.media_type,
        width=val_img.width,
        height=val_img.height,
        original_filename=val_img.original_filename,
    )

    analyzer = FrequencyAnalyzer()
    result = analyzer.analyze(context)

    assert result.status == "ok"
    assert result.id == "frequency"
    assert "mean_magnitude" in result.result
    assert result.artifact is not None
    assert "fft.jpg" in result.artifact


def test_runner_integrates_all() -> None:
    """Test runner executes all analyzers and produces indicators."""
    val_img = create_test_image("JPEG")
    indicators = run_all_analyzers(val_img, "test-scan-uuid")

    assert len(indicators) == 4
    ids = {ind.id for ind in indicators}
    assert ids == {"metadata", "ela", "noise", "frequency"}
    for ind in indicators:
        assert ind.status == "ok"