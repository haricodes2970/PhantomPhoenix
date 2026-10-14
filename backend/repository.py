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

    async def list_scans(self, limit: int = 20, cursor: str | None = None) -> tuple[list[Scan], str | None]:
        """
        List scans newest first with cursor-based pagination.

        Returns (scans, next_cursor).
        Cursor is ISO timestamp of the last item in the page.
        """
        stmt = select(Scan).order_by(Scan.created_at.desc()).limit(limit + 1)

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