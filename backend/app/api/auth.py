"""Authentication utilities and dependencies."""

import uuid
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.connection import get_db
from app.db.models import User

settings = get_settings()
logger = get_logger(__name__)

security = HTTPBearer()


def create_access_token(user_id: str) -> str:
    """
    Create JWT access token.

    Args:
        user_id: User ID

    Returns:
        JWT token
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {
        "sub": user_id,
        "exp": expire,
    }
    return str(jwt.encode(to_encode, settings.secret_key, algorithm="HS256"))


def decode_access_token(token: str) -> str:
    """
    Decode JWT access token.

    Args:
        token: JWT token

    Returns:
        User ID

    Raises:
        HTTPException: If token is invalid
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
        return user_id
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from e


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Get current authenticated user.

    Args:
        credentials: HTTP authorization credentials
        db: Database session

    Returns:
        Current user

    Raises:
        HTTPException: If user is not authenticated
    """
    user_id = decode_access_token(credentials.credentials)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current authenticated admin user.

    Args:
        current_user: Current user

    Returns:
        Current admin user

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def get_or_create_dev_user(db: Session, email: str) -> User:
    """
    Get or create a development user (for MVP/testing).

    Args:
        db: Database session
        email: User email

    Returns:
        User
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            is_active=True,
            is_admin=email.endswith("@admin.com"),  # Simple admin check for dev
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Created dev user", email=email, is_admin=user.is_admin)
    return user
