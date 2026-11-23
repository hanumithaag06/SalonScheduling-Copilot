# Why: Sets up the async SQLAlchemy engine and session factory.
# Every request gets its own session via the get_db() dependency.

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings

# create_async_engine: opens a connection pool to Postgres.
# echo=True in dev prints SQL statements to the console (great for debugging).
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

# async_sessionmaker: a factory that produces AsyncSession objects.
# expire_on_commit=False means objects stay usable after commit
# (otherwise accessing an attribute after commit triggers a lazy load error).
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """
    FastAPI dependency that yields one DB session per request.
    The 'async with' block auto-closes the session when the request ends,
    even if an exception is raised — no leaked connections.
    """
    async with AsyncSessionLocal() as session:
        yield session

