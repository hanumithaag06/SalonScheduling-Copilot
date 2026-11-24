# Why: User registration, login, and profile (/auth/me) endpoints.
# Enforces unique emails (409) and validates credentials with bcrypt (401).

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ConflictException, UnauthorizedException
from app.core.security import hash_password, verify_password, create_access_token
from app.db.session import get_db
from app.models import User
from app.schemas.auth import UserRegister, UserLogin, UserOut, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    Register a new customer (or admin if specified).
    Returns 409 Conflict with EMAIL_EXISTS if email is already taken.
    """
    stmt = select(User).where(User.email == payload.email)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise ConflictException(
            detail="A user with this email address already exists",
            code="EMAIL_EXISTS"
        )

    user = User(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": user.email, "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user via email and password.
    Returns 401 Unauthorized with INVALID_CREDENTIALS on mismatch.
    """
    stmt = select(User).where(User.email == payload.email)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedException(
            detail="Invalid email or password",
            code="INVALID_CREDENTIALS"
        )

    token = create_access_token({"sub": user.email, "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns the profile of the currently logged-in user.
    """
    return UserOut.model_validate(current_user)

