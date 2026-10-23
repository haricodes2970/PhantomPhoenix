"""Reset database users and keep only hari-phoenix / hari."""

from __future__ import annotations

import asyncio
from sqlalchemy import delete
from backend.database import async_session_factory, close_db, init_db
from backend.models import User, Scan, AuditEvent
from backend.auth import _ph


async def reset_users() -> None:
    await init_db()
    try:
        async with async_session_factory() as session:
            # Delete scans, audit events, and users
            await session.execute(delete(Scan))
            await session.execute(delete(AuditEvent))
            await session.execute(delete(User))
            
            # Create single user hari-phoenix with password hari
            password_hash = _ph.hash("hari")
            user = User(
                username="hari-phoenix",
                password_hash=password_hash,
                role="admin",
                is_enabled=True,
            )
            session.add(user)
            await session.commit()
            print("Successfully deleted all users and created user 'hari-phoenix' (password: hari, role: admin).")
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(reset_users())