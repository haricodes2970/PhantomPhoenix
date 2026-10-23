"""SQLAlchemy models for scan persistence."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class User(Base):
    """Authentication user (Milestone 12).

    Passwords are stored ONLY as Argon2id hashes. Username is normalized to
    lowercase at the application layer before persistence.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class AuditEvent(Base):
    """Persistent security-audit trail (Milestone 14).

    TRUST BOUNDARY (explicit): this is an application-auditable record store,
    NOT a tamper-proof ledger — a database administrator can always modify the
    underlying table. No ordinary-user application route reads or writes it;
    there are no update/delete application routes.

    Bounded, fixed-charset values only (validated in backend/audit.py): never
    passwords, tokens, cookies, image bytes, raw bodies, TLS-level EXIF data,
    or unbounded user input.
    """

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    # Actor reference; SET NULL so events survive user deletion.
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_audit_events_created_at_desc", created_at.desc()),
    )


class Scan(Base):
    """Scan record with all analysis results stored as JSONB."""

    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="complete")

    # Input image metadata
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(nullable=False)
    width: Mapped[int] = mapped_column(nullable=False)
    height: Mapped[int] = mapped_column(nullable=False)

    # Model output (stored as JSONB for flexibility)
    model_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_revision: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fake_probability: Mapped[float | None] = mapped_column(nullable=True)
    raw_logit: Mapped[float | None] = mapped_column(nullable=True)
    model_device: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model_duration_seconds: Mapped[float | None] = mapped_column(nullable=True)
    model_limitations: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    threshold_policy: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Verdict
    verdict_label: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    verdict_risk: Mapped[str] = mapped_column(String(32), nullable=False)
    verdict_rationale: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    verdict_not_claimed: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Error info (if any)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Ownership (nullable: legacy scans created before Milestone 12 have no owner;
    # unowned scans are administrator-accessible only — see backend/auth.py policy)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Full structured result for exact API compatibility
    full_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_scans_created_at_desc", created_at.desc()),
        Index("ix_scans_sha256_created_at", sha256, created_at.desc()),
    )

    def to_scan_result(self) -> dict[str, Any]:
        """Convert to the API ScanResult schema dict."""
        if self.full_result:
            return self.full_result
        # Fallback: reconstruct from columns (for records created before full_result)
        return {
            "scan_id": str(self.id),
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "input": {
                "sha256": self.sha256,
                "filename": self.filename,
                "media_type": self.media_type,
                "byte_size": self.byte_size,
                "width": self.width,
                "height": self.height,
            },
            "models": [
                {
                    "model_id": self.model_id,
                    "model_revision": self.model_revision,
                    "role": "primary",
                    "status": self.model_status,
                    "fake_probability": self.fake_probability,
                    "raw_logit": self.raw_logit,
                    "threshold_policy": self.threshold_policy,
                    "limitations": self.model_limitations or [],
                    "device": self.model_device,
                    "duration_seconds": self.model_duration_seconds,
                }
            ] if self.model_id else [],
            "indicators": [],
            "explainability": {"status": "unavailable", "kind": None, "artifact": None},
            "verdict": {
                "label": self.verdict_label,
                "risk": self.verdict_risk,
                "rationale": self.verdict_rationale or [],
                "not_claimed": self.verdict_not_claimed or [],
            },
            "error": self.error,
        }