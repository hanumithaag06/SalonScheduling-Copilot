# Why: Authentication and authorization dependencies.
# Injects current user and verifies admin permissions for protected endpoints.

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import UnauthorizedException, ForbiddenException
from app.db.session import get_db
from app.models import User

# OAuth2 scheme extracts token from Authorization: Bearer <token> header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validates JWT access token and retrieves the current authenticated user.
    Raises 401 UNAUTHORIZED if token is missing, expired, or invalid.
    """
    if not token:
        raise UnauthorizedException(
            detail="Missing or invalid authentication token",
            code="UNAUTHORIZED"
        )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise UnauthorizedException(
                detail="Token is missing user identifier",
                code="INVALID_TOKEN"
            )
    except JWTError:
        raise UnauthorizedException(
            detail="Token signature or expiration invalid",
            code="INVALID_TOKEN"
        )

    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise UnauthorizedException(
            detail="User account does not exist",
            code="USER_NOT_FOUND"
        )

    return user


async def get_optional_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Attempts to retrieve the authenticated user from JWT token if provided.
    Returns None if token is omitted, invalid, or expired, allowing guest access.
    """
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None

    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Ensures the authenticated user has the 'admin' role.
    Raises 403 FORBIDDEN if the user is a regular customer.
    """
    if current_user.role != "admin":
        raise ForbiddenException(
            detail="Administrative privileges required to access this resource",
            code="FORBIDDEN"
        )
    return current_user

