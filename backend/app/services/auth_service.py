"""Authentication service for credential verification and user provisioning."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthenticationError
from app.core.security import (
    DEMO_PASSWORDS,
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.platform import User
from app.schemas.auth import TokenResponse

logger = logging.getLogger(__name__)


async def authenticate_user(session: AsyncSession, username: str, password: str) -> TokenResponse:
    """Authenticate credentials and generate JWT token."""
    stmt = select(User).where(User.username == username)
    result = await session.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise AuthenticationError("Invalid username or password")

    if not verify_password(password, user.password_hash, username=username):
        raise AuthenticationError("Invalid username or password")

    # Generate token with user claims
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "user_id": user.id}
    )

    return TokenResponse(
        access_token=access_token,
        role=user.role,
        username=user.username,
    )


async def ensure_demo_users_exist(session: AsyncSession) -> None:
    """Ensure standard demo role accounts exist in the database."""
    roles = [
        ("commander", "commander"),
        ("planner", "planner"),
        ("technician", "technician"),
    ]

    for username, role in roles:
        stmt = select(User).where(User.username == username)
        res = await session.execute(stmt)
        user = res.scalars().first()

        raw_pwd = DEMO_PASSWORDS.get(username, "password123")
        pwd_hash = hash_password(raw_pwd)

        if not user:
            new_user = User(username=username, password_hash=pwd_hash, role=role)
            session.add(new_user)
            logger.info(f"Provisioned demo user: {username} ({role})")
        else:
            # Upgrade placeholder hash to standard hash
            if not user.password_hash.startswith("pbkdf2_sha256$"):
                user.password_hash = pwd_hash

    await session.commit()
