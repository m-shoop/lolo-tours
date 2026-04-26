"""Bootstrap an admin user.

Usage:
    python -m scripts.seed_admin_user --email admin@example.com --full-name "Jane Doe"

Prompts for a password (hidden). Creates the user if missing, sets the password,
and assigns the 'admin' role. Idempotent — re-running updates the password.
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Role, User, UserRole
from app.services.auth_service import hash_password


async def upsert_admin(
    db: AsyncSession, email: str, full_name: str, password: str
) -> User:
    email = email.lower().strip()

    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            is_active=True,
        )
        db.add(user)
        await db.flush()
        print(f"Created user {email} ({user.id})")
    else:
        user.hashed_password = hash_password(password)
        user.full_name = full_name
        user.is_active = True
        print(f"Updated existing user {email} ({user.id})")

    admin_role = (
        await db.execute(select(Role).where(Role.name == "admin"))
    ).scalar_one_or_none()
    if admin_role is None:
        raise RuntimeError(
            "Admin role not found. Run `alembic upgrade head` first."
        )

    existing_link = (
        await db.execute(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == admin_role.id,
            )
        )
    ).scalar_one_or_none()
    if existing_link is None:
        db.add(UserRole(user_id=user.id, role_id=admin_role.id))
        print(f"Assigned admin role to {email}")
    else:
        print(f"{email} already has admin role")

    return user


async def main() -> int:
    parser = argparse.ArgumentParser(description="Seed an admin user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    args = parser.parse_args()

    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        return 1
    if len(password) < 12:
        print("Password must be at least 12 characters.", file=sys.stderr)
        return 1

    async with AsyncSessionLocal() as db:
        await upsert_admin(db, args.email, args.full_name, password)
        await db.commit()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
