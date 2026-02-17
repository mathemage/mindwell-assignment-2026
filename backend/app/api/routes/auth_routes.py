"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import create_access_token, get_current_user, get_or_create_dev_user
from app.api.schemas.schemas import LoginRequest, TokenResponse, UserResponse
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.connection import get_db
from app.db.models import User

settings = get_settings()
logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Login endpoint (MVP: simplified dev login).

    In production, this would:
    - Send magic link via email
    - Verify magic link token
    - Return access token

    For MVP, we create/get user and return token directly.
    """
    if not settings.is_development:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Production auth not implemented yet",
        )

    logger.info("Dev login", email=request.email)

    # For MVP: get or create user
    user = get_or_create_dev_user(db, request.email)

    # Create access token
    token = create_access_token(user.id)

    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        pseudonym=current_user.pseudonym,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at,
    )
