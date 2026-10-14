"""Test configuration and fixtures."""

from __future__ import annotations

import io
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_session
from backend.detector import DetectorAdapter
from backend.main import app, get_detector_dependency
from backend.models import Scan
from backend.schemas import ModelOutput, VerdictLabel, RiskLevel


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create a mocked async database session."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture(autouse=True)
def override_db_session_for_unit_tests(request, mock_db_session: AsyncMock) -> Generator[None, None, None]:
    """Override database session for non-database integration tests."""
    if "test_database.py" not in str(request.path):
        app.dependency_overrides[get_session] = lambda: mock_db_session
        yield
        app.dependency_overrides.pop(get_session, None)
    else:
        yield


@pytest.fixture
def mock_detector(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Create a mocked detector adapter."""
    mock = MagicMock(spec=DetectorAdapter)

    # Mock health_info
    mock.health_info.return_value = {
        "detector_loaded": True,
        "detector_configured": True,
        "detector_model_id": "buildborderless/CommunityForensics-DeepfakeDet-ViT",
        "cuda_available": True,
        "gpu_name": "NVIDIA RTX 3050",
        "load_error": None,
    }

    # Mock infer - default returns a fake probability of 0.1 (LIKELY_REAL)
    mock.infer.return_value = ModelOutput(
        model_id="buildborderless/CommunityForensics-DeepfakeDet-ViT",
        model_revision="buildborderless/CommunityForensics-DeepfakeDet-ViT",
        role="primary",
        status="ok",
        fake_probability=0.1,
        raw_logit=-2.197,
        threshold_policy="0.80 likely_ai / 0.20 likely_real",
        limitations=["Not calibrated on images from this deployment"],
        device="cpu",
        duration_seconds=0.1,
    )

    # Replace the get_detector_dependency
    app.dependency_overrides[get_detector_dependency] = lambda: mock

    yield mock

    # Cleanup
    app.dependency_overrides.pop(get_detector_dependency, None)


@pytest.fixture
def mock_detector_high_score(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mocked detector returning high fake probability (LIKELY_AI)."""
    mock = MagicMock(spec=DetectorAdapter)

    mock.health_info.return_value = {
        "detector_loaded": True,
        "detector_configured": True,
        "detector_model_id": "buildborderless/CommunityForensics-DeepfakeDet-ViT",
        "cuda_available": True,
        "gpu_name": "NVIDIA RTX 3050",
        "load_error": None,
    }

    mock.infer.return_value = ModelOutput(
        model_id="buildborderless/CommunityForensics-DeepfakeDet-ViT",
        model_revision="buildborderless/CommunityForensics-DeepfakeDet-ViT",
        role="primary",
        status="ok",
        fake_probability=0.95,
        raw_logit=2.944,
        threshold_policy="0.80 likely_ai / 0.20 likely_real",
        limitations=["Not calibrated on images from this deployment"],
        device="cpu",
        duration_seconds=0.1,
    )

    app.dependency_overrides[get_detector_dependency] = lambda: mock

    yield mock

    app.dependency_overrides.pop(get_detector_dependency, None)


@pytest.fixture
def mock_detector_mid_score(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mocked detector returning mid-range probability (INCONCLUSIVE)."""
    mock = MagicMock(spec=DetectorAdapter)

    mock.health_info.return_value = {
        "detector_loaded": True,
        "detector_configured": True,
        "detector_model_id": "buildborderless/CommunityForensics-DeepfakeDet-ViT",
        "cuda_available": True,
        "gpu_name": "NVIDIA RTX 3050",
        "load_error": None,
    }

    mock.infer.return_value = ModelOutput(
        model_id="buildborderless/CommunityForensics-DeepfakeDet-ViT",
        model_revision="buildborderless/CommunityForensics-DeepfakeDet-ViT",
        role="primary",
        status="ok",
        fake_probability=0.5,
        raw_logit=0.0,
        threshold_policy="0.80 likely_ai / 0.20 likely_real",
        limitations=["Not calibrated on images from this deployment"],
        device="cpu",
        duration_seconds=0.1,
    )

    app.dependency_overrides[get_detector_dependency] = lambda: mock

    yield mock

    app.dependency_overrides.pop(get_detector_dependency, None)


@pytest.fixture
def mock_detector_error(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mocked detector that raises an inference error."""
    from backend.detector import InferenceError

    mock = MagicMock(spec=DetectorAdapter)

    mock.health_info.return_value = {
        "detector_loaded": False,
        "detector_configured": False,
        "detector_model_id": None,
        "cuda_available": True,
        "gpu_name": "NVIDIA RTX 3050",
        "load_error": "Model load failed",
    }

    mock.infer.side_effect = InferenceError("Model failed to load")

    app.dependency_overrides[get_detector_dependency] = lambda: mock

    yield mock

    app.dependency_overrides.pop(get_detector_dependency, None)


def create_test_image(
    width: int = 512,
    height: int = 512,
    color: tuple[int, int, int] = (128, 128, 128),
    format: str = "JPEG",
) -> io.BytesIO:
    """Create a test image in memory."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf


def create_test_image_bytes(
    width: int = 512,
    height: int = 512,
    color: tuple[int, int, int] = (128, 128, 128),
    format: str = "JPEG",
) -> bytes:
    """Create test image bytes."""
    return create_test_image(width, height, color, format).getvalue()