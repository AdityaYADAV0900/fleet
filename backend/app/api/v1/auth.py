"""Authentication and session management API router."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.platform import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.services.auth_service import authenticate_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, summary="Obtain JWT access token")
async def login(
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Authenticate with username and password to receive a bearer JWT token."""
    return await authenticate_user(session, username=payload.username, password=payload.password)


@router.get("/me", response_model=UserOut, summary="Get current user details")
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserOut:
    """Return identity and assigned role for the authenticated user."""
    return UserOut.model_validate(current_user)
