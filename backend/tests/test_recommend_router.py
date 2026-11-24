# Why: Integration tests for the GET /recommend endpoint.
# Verifies candidate retrieval, multi-factor scoring (loyalty, time preference,
# specialization, gap adjacency), explanation payload, budget filtering, and 404 behavior.

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import pytest
from app.models import Service, Stylist, stylist_services, WorkingHours, Booking, User
from app.core.security import hash_password, create_access_token


def get_next_monday_iso() -> str:
    """Returns the ISO string for the next upcoming Monday so tests run safely in the future."""
    today = datetime.now(timezone.utc).date()
    days_ahead = (0 - today.weekday()) % 7 or 7
    return (today + timedelta(days=days_ahead)).isoformat()


@pytest.fixture
async def setup_recommend_data(db_session):
    """Sets up services, stylists with distinct specializations and shifts, and a registered customer."""
    # 1. Customer
    customer = User(
        name="Charlie Client",
        email="charlie.recommend@example.com",
        phone="+12025550199",
        password_hash=hash_password("password123"),
        role="customer",
    )
    db_session.add(customer)
    await db_session.flush()

    # 2. Services
    color_service = Service(
        name="Balayage Hair Color",
        category="Coloring",
        duration_min=60,
        price=Decimal("150.00"),
        is_active=True,
    )
    db_session.add(color_service)
    await db_session.flush()

    # 3. Stylists
    # Alice: Color Specialist
    alice = Stylist(
        name="Alice Colorist",
        specialization="Hair Color Specialist & Balayage",
        is_active=True,
    )
    # Bob: Barber Specialist
    bob = Stylist(
        name="Bob Barber",
        specialization="Classic Barber Cuts & Beard",
        is_active=True,
    )
    db_session.add_all([alice, bob])
    await db_session.flush()

    # 4. Associate both stylists with the service
    await db_session.execute(
        stylist_services.insert(),
        [
            {"stylist_id": alice.id, "service_id": color_service.id},
            {"stylist_id": bob.id, "service_id": color_service.id},
        ]
    )

    # 5. Working hours: Monday (0) 09:00 - 18:00
    wh_a = WorkingHours(stylist_id=alice.id, weekday=0, start_time=time(9, 0), end_time=time(18, 0))
    wh_b = WorkingHours(stylist_id=bob.id, weekday=0, start_time=time(9, 0), end_time=time(18, 0))
    db_session.add_all([wh_a, wh_b])
    await db_session.commit()

    return {
        "customer": customer,
        "service": color_service,
        "alice": alice,
        "bob": bob,
    }


@pytest.mark.asyncio
async def test_recommend_endpoint_basic(client, setup_recommend_data):
    """GET /recommend returns up to 3 scored recommendations with reasons."""
    data = setup_recommend_data
    target_date = get_next_monday_iso()

    response = await client.get(
        "/recommend",
        params={
            "service_id": data["service"].id,
            "date": target_date,
            "lead_time_min": 0,
        },
    )

    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert 1 <= len(results) <= 3

    # Check top recommendation structure
    top = results[0]
    assert "score" in top
    assert "score_breakdown" in top
    assert "reason" in top
    assert top["price"] == "150.00"

    # Alice should score +1 for specialization match over Bob
    assert top["stylist_id"] == data["alice"].id
    assert top["score_breakdown"]["specialization"] == 1.0
    assert "specializes in" in top["reason"]


@pytest.mark.asyncio
async def test_recommend_preferred_time(client, setup_recommend_data):
    """Passing preferred_time awards +2 to matching time slots."""
    data = setup_recommend_data
    target_date = get_next_monday_iso()

    response = await client.get(
        "/recommend",
        params={
            "service_id": data["service"].id,
            "date": target_date,
            "preferred_time": "afternoon",
            "lead_time_min": 0,
        },
    )

    assert response.status_code == 200
    results = response.json()
    assert len(results) > 0

    top = results[0]
    # Check that top recommendation earned the preferred_time bonus
    assert top["score_breakdown"]["preferred_time"] == 2.0
    assert "afternoon" in top["reason"].lower()


@pytest.mark.asyncio
async def test_recommend_loyalty_boost(client, setup_recommend_data, db_session):
    """Logged in user with past visits to a stylist gets loyalty points (+1/visit up to +3)."""
    data = setup_recommend_data
    customer = data["customer"]
    bob = data["bob"]
    color_service = data["service"]
    target_date = get_next_monday_iso()

    # Seed 2 completed past bookings for customer with Bob
    b1 = Booking(
        user_id=customer.id,
        stylist_id=bob.id,
        service_id=color_service.id,
        start_ts=datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc),
        end_ts=datetime(2026, 1, 10, 11, 0, tzinfo=timezone.utc),
        status="completed",
    )
    b2 = Booking(
        user_id=customer.id,
        stylist_id=bob.id,
        service_id=color_service.id,
        start_ts=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
        end_ts=datetime(2026, 1, 15, 11, 0, tzinfo=timezone.utc),
        status="completed",
    )
    db_session.add_all([b1, b2])
    await db_session.commit()

    # Authenticate as Charlie
    token = create_access_token(data={"sub": customer.email, "role": customer.role})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(
        "/recommend",
        params={
            "service_id": color_service.id,
            "date": target_date,
            "lead_time_min": 0,
        },
        headers=headers,
    )

    assert response.status_code == 200
    results = response.json()
    top = results[0]

    # Bob should now be #1 because loyalty (+2.0) beats Alice's specialization (+1.0)
    assert top["stylist_id"] == bob.id
    assert top["score_breakdown"]["past_bookings"] == 2.0
    assert "2 times before" in top["reason"]


@pytest.mark.asyncio
async def test_recommend_max_price_filter(client, setup_recommend_data):
    """If service price exceeds max_price, an empty list is returned."""
    data = setup_recommend_data
    target_date = get_next_monday_iso()

    response = await client.get(
        "/recommend",
        params={
            "service_id": data["service"].id,
            "date": target_date,
            "max_price": "100.00",  # Service costs 150.00
            "lead_time_min": 0,
        },
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_recommend_service_not_found(client):
    """GET /recommend with an unknown service ID returns 404 with standard error format."""
    response = await client.get(
        "/recommend",
        params={
            "service_id": 99999,
            "date": get_next_monday_iso(),
            "lead_time_min": 0,
        },
    )

    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "SERVICE_NOT_FOUND"
    assert "detail" in data
