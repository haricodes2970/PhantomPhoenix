"""Application configuration via Pydantic Settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 1

    # Database
    database_url: str = "postgresql+asyncpg://phantom:phantom@localhost:5432/phantom_phoenix"
    database_echo: bool = False

    # Model
    model_id: str = "buildborderless/CommunityForensics-DeepfakeDet-ViT"
    device: str = "auto"  # auto, cuda, cpu
    max_image_size_mb: int = 15
    max_dimension_px: int = 8192

    # Verdict thresholds (provisional screening, not calibrated)
    likely_ai_threshold: float = 0.80
    likely_real_threshold: float = 0.20

    # Allowed MIME types (validated by decode, not by header)
    allowed_mime_types: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp")


settings = Settings()