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
    model_revision: str = "ac6ee457bea904a373065754107451793b56db00"
    device: str = "auto"  # auto, cuda, cpu
    max_image_size_mb: int = 5
    max_dimension_px: int = 8192

    # Verdict thresholds (validated on hold-out validation set; not calibrated probabilities)
    likely_ai_threshold: float = 0.80
    likely_real_threshold: float = 0.05

    # Allowed MIME types (validated by decode, not by header)
    allowed_mime_types: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp")

    # CORS origins (comma-separated). Staging/TLS proxies MUST add their own
    # public origin here, e.g. https://localhost:8443
    cors_origins_csv: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000"

    # Authentication (Milestone 12)
    # HS256 signing secret. MUST be set via environment/.env in any real run;
    # auth endpoints fail safely (503) when absent or shorter than 32 chars.
    auth_secret: str = ""
    access_token_expire_minutes: int = 30
    # Cookie flags: secure must be enabled behind HTTPS (production).
    cookie_secure: bool = False
    # Rate limits: "<count>/<window>" where window ∈ {second, minute, hour}
    rate_limit_login_per_minute: int = 5
    rate_limit_scan_per_minute: int = 10
    rate_limit_default_per_minute: int = 120


settings = Settings()