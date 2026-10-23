"""One-time administrator bootstrap CLI (Milestone 12).

Purpose: create the initial administrator account without any default or
public password. Run interactively:

  # from the host (requires a running postgres + backend env):
  PYTHONPATH=. .venv/bin/python -m backend.bootstrap_admin

  # inside the running containerized stack:
  docker compose exec backend python -m backend.bootstrap_admin

The command prompts for username and password (hidden input, confirmation),
validates password strength, hashes with Argon2id, and inserts the user.
It NEVER prints or logs the password. Re-running prompts for an existing
username updates its password only after interactive confirmation, or
exits without changes.
"""

from __future__ import annotations

import asyncio
import getpass
import sys

from sqlalchemy import select

from backend.auth import WeakPasswordError, hash_password
from backend.database import async_session_factory, close_db, init_db
from backend.models import User

STATIC_USERNAME_MAX = 64


def _prompt_username() -> str:
    username = input("Administrator username: ").strip().lower()
    if not username or len(username) > STATIC_USERNAME_MAX or not username.replace("-", "").replace("_", "").isalnum():
        raise SystemExit("Invalid username (1-64 chars, letters/digits/'-'/'_').")
    return username


def _prompt_password() -> str:
    password = getpass.getpass("Administrator password (min 12 chars): ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match.")
    return password


async def bootstrap() -> None:
    username = _prompt_username()
    password = _prompt_password()

    await init_db()
    try:
        async with async_session_factory() as session:
            existing = (await session.execute(select(User).where(User.username == username))).scalar_one_or_none()
            if existing is not None:
                raise SystemExit(f"User '{username}' already exists. No changes made.")
            try:
                user = User(
                    username=username,
                    password_hash=hash_password(password),
                    role="admin",
                    is_enabled=True,
                )
            except WeakPasswordError:
                raise SystemExit("Password rejected: minimum 12 characters.")
            session.add(user)
            await session.commit()
            from backend.audit import record_audit_event
            await record_audit_event(
                "admin_bootstrap",
                outcome="success",
                actor_user_id=str(user.id),
                actor_role="admin",
                detail=f"user={username}",
            )
            print(f"Administrator '{username}' created (role=admin). Store credentials securely.")
    finally:
        await close_db()


def main() -> None:
    try:
        asyncio.run(bootstrap())
    except SystemExit as exc:
        print(str(exc))
        sys.exit(1 if isinstance(exc.code, int) else 0)


if __name__ == "__main__":
    main()
