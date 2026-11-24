# Why: Integration tests for the AI assistant endpoints (POST /assistant/parse and /assistant/suggest).
# Verifies fallback parsing, budget filters, follow-up clarification for missing fields,
# and strictly enforces that the assistant NEVER creates booking rows before user confirmation.

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy import select, func

from app.models import Service, Stylist, stylist_services, WorkingHours, Booking, User
from app.core.security import hash_password, create_access_token


def get_next_monday() -> date:
    today = datetime.now(timezone.utc).date()
    days_ahead = (0 - today.weekday()) % 7 or 7
    return today + timedelta(days=days_ahead)


@pytest.fixture
async def setup_assistant_data(db_session):
    """Sets up customer, service, stylist, and working hours."""
    customer = User(
        name="Alex Client",
        email="alex.client@example.com",
        phone="+12025550300",
        password_hash=hash_password("password123"),
        role="customer",
    )
    service = Service(
        name="Classic Haircut",
        category="Hair",
        duration_min=30,
        price=Decimal("35.00"),
        is_active=True,
    )
    expensive_service = Service(
        name="Keratin Smoothing Treatment",
        category="Treatments",
        duration_min=90,
        price=Decimal("160.00"),
        is_active=True,
    )
    stylist = Stylist(
        name="Jordan Master",
        specialization="Haircuts & Keratin",
        is_active=True,
    )
    db_session.add_all([customer, service, expensive_service, stylist])
    await db_session.flush()

    await db_session.execute(
        stylist_services.insert(),
        [
            {"stylist_id": stylist.id, "service_id": service.id},
            {"stylist_id": stylist.id, "service_id": expensive_service.id},
        ]
    )

    # Monday 09:00 - 18:00
    target_monday = get_next_monday()
    wh = WorkingHours(
        stylist_id=stylist.id,
        weekday=target_monday.weekday(),
        start_time=time(9, 0),
        end_time=time(18, 0),
    )
    db_session.add(wh)
    await db_session.commit()

    return {
        "customer": customer,
        "service": service,
        "expensive_service": expensive_service,
        "stylist": stylist,
    }


@pytest.mark.asyncio
async def test_assistant_parse_endpoint(client, setup_assistant_data):
    """POST /assistant/parse extracts intent using keyword/date fallback when no LLM key."""
    target_date = get_next_monday().isoformat()
    resp = await client.post(
        "/assistant/parse",
        json={"message": f"I want a classic haircut on {target_date} afternoon under $50"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "Classic Haircut"
    assert data["date"] == target_date
    assert data["time_pref"] == "afternoon"
    assert Decimal(data["max_price"]) == Decimal("50")
    assert data["missing_fields"] == []
    assert data["source"] == "keyword_fallback"


@pytest.mark.asyncio
async def test_assistant_parse_missing_fields_asks_followup(client):
    """When required fields are missing, returns follow_up_question without guessing."""
    resp = await client.post(
        "/assistant/parse",
        json={"message": "Can I get an appointment please?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "service" in data["missing_fields"]
    assert "date" in data["missing_fields"]
    assert data["follow_up_question"] is not None
    assert "?" in data["follow_up_question"]


@pytest.mark.asyncio
async def test_assistant_suggest_missing_fields_returns_question(client, setup_assistant_data):
    """POST /assistant/suggest with incomplete query returns clarifying question and no suggestions."""
    resp = await client.post(
        "/assistant/suggest",
        json={"message": "I'd like a haircut"},  # missing date
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["suggestions"]) == 0
    assert data["follow_up_question"] is not None
    assert "date" in data["intent"]["missing_fields"]


@pytest.mark.asyncio
async def test_assistant_suggest_budget_filter(client, setup_assistant_data):
    """When service price exceeds budget, assistant informs user and returns 0 suggestions."""
    target_date = get_next_monday().isoformat()
    # Keratin costs $160, user specifies budget of 100
    resp = await client.post(
        "/assistant/suggest",
        json={"message": f"Keratin smoothing treatment on {target_date} under $100"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["suggestions"]) == 0
    assert "exceeds your budget" in data["message"]


@pytest.mark.asyncio
async def test_assistant_suggest_returns_ranked_options(client, setup_assistant_data):
    """POST /assistant/suggest returns top recommendations with reasons."""
    target_date = get_next_monday().isoformat()
    resp = await client.post(
        "/assistant/suggest",
        json={"message": f"Classic haircut on {target_date} morning under $50"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["suggestions"]) > 0
    first_opt = data["suggestions"][0]
    assert "score" in first_opt
    assert "reason" in first_opt
    assert "booking_instructions" in data


@pytest.mark.asyncio
async def test_assistant_never_creates_booking_before_user_confirmation(
    client, setup_assistant_data, db_session
):
    """
    CRITICAL ARCHITECTURAL GUARD:
    Calling /assistant/suggest multiple times MUST NEVER create or insert any booking rows.
    Bookings only occur through explicit POST /bookings.
    """
    target_date = get_next_monday().isoformat()

    # 1. Count bookings before assistant calls
    count_before = (await db_session.execute(select(func.count(Booking.id)))).scalar()

    # 2. Call suggest 3 times
    for _ in range(3):
        resp = await client.post(
            "/assistant/suggest",
            json={"message": f"Classic haircut on {target_date} morning"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["suggestions"]) > 0

    # 3. Count bookings after assistant calls — must be IDENTICAL
    count_after = (await db_session.execute(select(func.count(Booking.id)))).scalar()
    assert count_after == count_before

    # 4. Only explicit POST /bookings creates an appointment
    customer = setup_assistant_data["customer"]
    token = create_access_token({"sub": customer.email, "role": "customer"})
    service = setup_assistant_data["service"]
    stylist = setup_assistant_data["stylist"]
    start_ts = datetime.combine(get_next_monday(), time(10, 0), tzinfo=timezone.utc)

    book_resp = await client.post(
        "/bookings",
        json={
            "service_id": service.id,
            "stylist_id": stylist.id,
            "start_ts": start_ts.isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert book_resp.status_code == 201

    # 5. Count now incremented by exactly 1
    count_final = (await db_session.execute(select(func.count(Booking.id)))).scalar()
    assert count_final == count_before + 1
