# Why: Declares the single DeclarativeBase that ALL models inherit from.
# SQLAlchemy uses this base to discover tables for Alembic migrations.

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Every model class (User, Service, Booking, etc.) will subclass Base.
    Alembic's env.py imports Base.metadata to auto-generate migrations.
    """
    pass

