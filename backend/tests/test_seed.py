# Why: Tests for the seed.py logic to ensure dummy data loads cleanly
# and that re-running the seeder is safe and idempotent.

import pytest
from sqlalchemy import select, func
from app.models import User, Service, Stylist, WorkingHours, Booking, stylist_services
from app.core.security import verify_password
from seed import seed_data


@pytest.mark.asyncio
async def test_seed_loads_successfully(db_session):
    """Verifies that seed_data populates all expected entities."""
    summary = await seed_data(db_session)

    # 1. User verification (1 admin + 8 customers = 9 users)
    assert summary["users"] == 9
    users = (await db_session.execute(select(User))).scalars().all()
    assert len(users) == 9

    admins = [u for u in users if u.role == "admin"]
    customers = [u for u in users if u.role == "customer"]
    assert len(admins) == 1
    assert len(customers) == 8
    assert admins[0].email == "admin@stylify.com"

    # Verify password authentication works for seeded users
    assert verify_password("Password123!", admins[0].password_hash) is True
    assert verify_password("Password123!", customers[0].password_hash) is True

    # 2. Service verification (10 services)
    assert summary["services"] == 10
    services = (await db_session.execute(select(Service))).scalars().all()
    assert len(services) == 10
    categories = {s.category for s in services}
    assert "Hair" in categories
    assert "Color" in categories
    assert "Treatments" in categories
    assert "Nails" in categories

    # 3. Stylist verification (5 stylists with Mon-Sat working hours)
    assert summary["stylists"] == 5
    stylists = (await db_session.execute(select(Stylist))).scalars().all()
    assert len(stylists) == 5

    # Each stylist must have 6 working hour entries (Mon=0 to Sat=5)
    for st in stylists:
        wh_stmt = select(WorkingHours).where(WorkingHours.stylist_id == st.id)
        wh_entries = (await db_session.execute(wh_stmt)).scalars().all()
        assert len(wh_entries) == 6
        weekdays = {wh.weekday for wh in wh_entries}
        assert weekdays == {0, 1, 2, 3, 4, 5}

    # 4. Stylist-service associations exist
    assoc_count = (await db_session.execute(select(func.count()).select_from(stylist_services))).scalar_one()
    assert assoc_count >= 15  # average 3+ services per stylist

    # 5. Historical Bookings (~60 bookings over last 60 days)
    assert 45 <= summary["bookings"] <= 75
    bookings = (await db_session.execute(select(Booking))).scalars().all()
    assert len(bookings) == summary["bookings"]

    statuses = {b.status for b in bookings}
    assert "completed" in statuses
    assert "confirmed" in statuses


@pytest.mark.asyncio
async def test_seed_is_idempotent(db_session):
    """Verifies that running seed_data multiple times produces no errors or duplicates."""
    first_run = await seed_data(db_session)
    second_run = await seed_data(db_session)

    assert first_run["users"] == second_run["users"] == 9
    assert first_run["services"] == second_run["services"] == 10
    assert first_run["stylists"] == second_run["stylists"] == 5
    assert first_run["bookings"] == second_run["bookings"]
