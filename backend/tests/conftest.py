# Why: Shared pytest fixtures. Provides an isolated async test database session,
# FastAPI dependency overrides, and pre-authenticated test clients.

import sys
import asyncio
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.db.session import get_db
from app.models import Base, User
from app.core.security import hash_password, create_access_token

# On Windows, SelectorEventLoop prevents async socket hang issues
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_engine():
    """Creates a temporary in-memory SQLite engine with all tables created."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Yields an isolated async session for database operations within a test."""
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(db_session):
    """
    Async HTTP client with get_db dependency overridden to the test session.
    Bypasses the network stack for fast in-process execution.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_user(db_session):
    """Creates and returns an active admin user."""
    admin = User(
        name="Test Admin",
        email="testadmin@stylify.com",
        phone="+1-555-0999",
        password_hash=hash_password("AdminPass123!"),
        role="admin",
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
async def admin_headers(admin_user):
    """Returns authorization headers containing a valid admin JWT."""
    token = create_access_token({"sub": admin_user.email, "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def customer_user(db_session):
    """Creates and returns an active customer user."""
    customer = User(
        name="Test Customer",
        email="testcust@example.com",
        phone="+1-555-0888",
        password_hash=hash_password("CustPass123!"),
        role="customer",
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


@pytest.fixture
async def customer_headers(customer_user):
    """Returns authorization headers containing a valid customer JWT."""
    token = create_access_token({"sub": customer_user.email, "role": "customer"})
    return {"Authorization": f"Bearer {token}"}
