# Why: Unit tests for core data models, security helpers, and relationships.

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from sqlalchemy import select
from jose import jwt

from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.models import User, Service, Stylist, Booking, SlotHold, Waitlist, Notification, AuditLog


def test_password_hashing():
    """Bcrypt password hashing and verification."""
    password = "MySecurePassword2026!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_create_access_token():
    """JWT token creation contains user sub and expiration."""
    data = {"sub": "user@example.com", "role": "admin"}
    token = create_access_token(data, expires_delta=timedelta(minutes=15))

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == "user@example.com"
    assert payload["role"] == "admin"
    assert "exp" in payload


@pytest.mark.asyncio
async def test_user_and_booking_relationships(db_session):
    """Creates user, service, stylist, and booking, then navigates ORM relationships."""
    # 1. Create User
    user = User(
        name="Test Customer",
        email="test.customer@example.com",
        password_hash=hash_password("Pass123!"),
        role="customer"
    )
    db_session.add(user)

    # 2. Create Service
    service = Service(
        name="Express Trim",
        category="Hair",
        duration_min=20,
        price=Decimal("25.00"),
        is_active=True
    )
    db_session.add(service)

    # 3. Create Stylist
    stylist = Stylist(
        name="Alex River",
        specialization="Quick Cuts",
        is_active=True
    )
    db_session.add(stylist)
    await db_session.flush()

    # 4. Create Booking
    now = datetime.now(timezone.utc)
    booking = Booking(
        user_id=user.id,
        service_id=service.id,
        stylist_id=stylist.id,
        start_ts=now,
        end_ts=now + timedelta(minutes=20),
        status="confirmed",
        notes="First time customer"
    )
    db_session.add(booking)
    await db_session.commit()

    # Query and test relations
    stmt = select(Booking).where(Booking.id == booking.id)
    saved_booking = (await db_session.execute(stmt)).scalar_one()

    assert saved_booking.user.email == "test.customer@example.com"
    assert saved_booking.service.name == "Express Trim"
    assert saved_booking.stylist.name == "Alex River"
    assert saved_booking.status == "confirmed"


@pytest.mark.asyncio
async def test_slot_hold_model(db_session):
    """Tests SlotHold temporary reservation."""
    user = User(name="Hold User", email="hold@example.com", password_hash="hash", role="customer")
    stylist = Stylist(name="Hold Stylist", specialization="Hair", is_active=True)
    db_session.add_all([user, stylist])
    await db_session.flush()

    start = datetime.now(timezone.utc)
    hold = SlotHold(
        user_id=user.id,
        stylist_id=stylist.id,
        start_ts=start,
        end_ts=start + timedelta(minutes=45),
        expires_at=start + timedelta(minutes=5)
    )
    db_session.add(hold)
    await db_session.commit()

    assert hold.id is not None
    assert hold.expires_at > hold.start_ts
