"""Authentication dependencies and role-based access control (RBAC)."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AuthenticationError, ForbiddenError
from app.core.security import decode_access_token
from app.models.platform import User

# Use standard HTTP Bearer token
security_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_bearer)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Dependency that resolves the authenticated user from the Bearer JWT token."""
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Authorization header with Bearer token is required")

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise AuthenticationError("Invalid or expired authentication token")

    username = payload.get("sub")
    if not username:
        raise AuthenticationError("Token payload missing subject identifier")

    result = await session.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if not user:
        raise AuthenticationError(f"User '{username}' no longer exists")

    return user


def require_roles(*allowed_roles: str) -> Callable[[User], User]:
    """Dependency factory restricting route access to specified application roles."""

    def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenError(
                f"Role '{current_user.role}' lacks permission for this action. "
                f"Required one of: {', '.join(allowed_roles)}"
            )
        return current_user

    return role_checker
