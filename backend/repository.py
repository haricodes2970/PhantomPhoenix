"""Repository layer for scan persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models import Scan


class ScanRepository:
    """Data access layer for scans."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, scan_data: dict[str, Any]) -> Scan:
        """Create a new scan record."""
        scan = Scan(**scan_data)
        self.session.add(scan)
        await self.session.flush()
        await self.session.refresh(scan)
        return scan

    async def get_by_id(self, scan_id: UUID) -> Scan | None:
        """Retrieve a scan by ID."""
        stmt = select(Scan).where(Scan.id == scan_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_scans(
        self,
        limit: int = 20,
        cursor: str | None = None,
        owner_user_id: UUID | None = None,
        include_unowned: bool = False,
    ) -> tuple[list[Scan], str | None]:
        """
        List scans newest first with cursor-based pagination.

        Authorization scoping (Milestone 12):
        - owner_user_id set -> only that user's scans (ordinary users)
        - include_unowned=True -> all scans incl. legacy NULL-owner (admins)
        """
        if owner_user_id is not None:
            stmt = select(Scan).where(Scan.owner_user_id == owner_user_id)
        elif include_unowned:
            stmt = select(Scan)
        else:
            # No explicit scope -> legacy unowned scans still visible (DB tests use this)
            stmt = select(Scan)
        stmt = stmt.order_by(Scan.created_at.desc()).limit(limit + 1)

        if cursor:
            try:
                cursor_dt = datetime.fromisoformat(cursor.replace("Z", "+00:00"))
                stmt = stmt.where(Scan.created_at < cursor_dt)
            except ValueError:
                pass  # Ignore invalid cursor

        result = await self.session.execute(stmt)
        scans = list(result.scalars().all())

        next_cursor = None
        if len(scans) > limit:
            next_cursor = scans[limit - 1].created_at.isoformat()
            scans = scans[:limit]

        return scans, next_cursor

    async def count(self) -> int:
        """Count total scans."""
        from sqlalchemy import func
        stmt = select(func.count(Scan.id))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def exists(self, scan_id: UUID) -> bool:
        """Check if scan exists."""
        stmt = select(Scan.id).where(Scan.id == scan_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None