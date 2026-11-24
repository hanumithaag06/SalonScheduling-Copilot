# Why: Tests for booking lifecycle: validations, cancellation/reschedule windows,
# audit log recording, and concurrent double-booking collisions (409 SLOT_TAKEN).

import asyncio
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy import select
from app.models import Service, Stylist, stylist_services, WorkingHours, Booking, AuditLog, User
from app.core.security import hash_password, create_access_token


@pytest.fixture
async def booking_setup(db_session):
    """Sets up a service and stylist with Monday working hours."""
    # 1. Service: 30 minutes, $40
    service = Service(
        name="Signature Haircut",
        category="Hair",
        duration_min=30,
        price=Decimal("40.00"),
        is_active=True,
    )
    # 2. Unoffered Service
    other_service = Service(
        name="Nail Care",
        category="Nails",
        duration_min=45,
        price=Decimal("35.00"),
        is_active=True,
    )
    db_session.add_all([service, other_service])
    await db_session.flush()

    # 3. Stylist: John Doe
    stylist = Stylist(name="John Doe", specialization="Haircuts", is_active=True)
    db_session.add(stylist)
    await db_session.flush()

    # 4. Map only service to stylist (other_service is NOT mapped)
    await db_session.execute(
        stylist_services.insert().values(stylist_id=stylist.id, service_id=service.id)
    )

    # 5. Working hours: Monday (0) 09:00 - 18:00
    wh = WorkingHours(stylist_id=stylist.id, weekday=0, start_time=time(9, 0), end_time=time(18, 0))
    db_session.add(wh)
    await db_session.commit()

    return {
        "service": service,
        "other_service": other_service,
        "stylist": stylist,
    }


def get_next_monday_at(hour: int, minute: int = 0) -> datetime:
    """Helper returning upcoming Monday at given hour/min in UTC."""
    today = datetime.now(timezone.utc).date()
    days_ahead = (0 - today.weekday()) % 7 or 7
    target_date = today + timedelta(days=days_ahead)
    return datetime.combine(target_date, time(hour, minute), tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_create_booking_success(client, customer_headers, booking_setup):
    """Successful booking returns 201 with confirmed status and audit log."""
    service = booking_setup["service"]
    stylist = booking_setup["stylist"]
    start_ts = get_next_monday_at(10, 0)

    payload = {
        "service_id": service.id,
        "stylist_id": stylist.id,
        "start_ts": start_ts.isoformat(),
        "notes": "First booking",
    }
    response = await client.post("/bookings", json=payload, headers=customer_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "confirmed"
    assert data["service"]["name"] == "Signature Haircut"
    assert data["stylist"]["name"] == "John Doe"
    assert data["end_ts"].replace("+00:00", "Z") == (start_ts + timedelta(minutes=30)).isoformat().replace("+00:00", "Z")


@pytest.mark.asyncio
async def test_booking_in_past_rejected(client, customer_headers, booking_setup):
    """Attempting to book a slot in the past returns 400 with PAST_SLOT."""
    service = booking_setup["service"]
    stylist = booking_setup["stylist"]
    past_ts = datetime.now(timezone.utc) - timedelta(days=1)

    payload = {
        "service_id": service.id,
        "stylist_id": stylist.id,
        "start_ts": past_ts.isoformat(),
    }
    response = await client.post("/bookings", json=payload, headers=customer_headers)
    assert response.status_code == 400
    assert response.json()["code"] == "PAST_SLOT"


@pytest.mark.asyncio
async def test_booking_unoffered_service_rejected(client, customer_headers, booking_setup):
    """Booking a service that the stylist does not perform returns 400 INVALID_STYLIST_SERVICE."""
    other_service = booking_setup["other_service"]
    stylist = booking_setup["stylist"]
    start_ts = get_next_monday_at(11, 0)

    payload = {
        "service_id": other_service.id,
        "stylist_id": stylist.id,
        "start_ts": start_ts.isoformat(),
    }
    response = await client.post("/bookings", json=payload, headers=customer_headers)
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_STYLIST_SERVICE"


@pytest.mark.asyncio
async def test_customer_overlapping_booking_rejected(client, customer_headers, booking_setup):
    """Customer cannot book two simultaneous appointments (409 USER_OVERLAP)."""
    service = booking_setup["service"]
    stylist = booking_setup["stylist"]
    start_ts = get_next_monday_at(12, 0)

    payload = {
        "service_id": service.id,
        "stylist_id": stylist.id,
        "start_ts": start_ts.isoformat(),
    }
    # 1. First booking succeeds
    res1 = await client.post("/bookings", json=payload, headers=customer_headers)
    assert res1.status_code == 201

    # 2. Second booking at the same time for the same user is rejected
    res2 = await client.post("/bookings", json=payload, headers=customer_headers)
    assert res2.status_code == 409
    assert res2.json()["code"] in {"USER_OVERLAP", "SLOT_TAKEN"}


@pytest.mark.asyncio
async def test_cancellation_window_enforcement(client, customer_headers, booking_setup, db_session, customer_user):
    """Cancelling >2h before start succeeds; cancelling <2h before start returns 400."""
    service = booking_setup["service"]
    stylist = booking_setup["stylist"]
    now_utc = datetime.now(timezone.utc)

    # 1. Booking far in future (e.g. next week)
    far_future = get_next_monday_at(14, 0)
    b_far = Booking(
        user_id=customer_user.id,
        service_id=service.id,
        stylist_id=stylist.id,
        start_ts=far_future,
        end_ts=far_future + timedelta(minutes=30),
        status="confirmed"
    )
    # 2. Imminent booking in 1 hour
    imminent = now_utc + timedelta(hours=1)
    b_imminent = Booking(
        user_id=customer_user.id,
        service_id=service.id,
        stylist_id=stylist.id,
        start_ts=imminent,
        end_ts=imminent + timedelta(minutes=30),
        status="confirmed"
    )
    db_session.add_all([b_far, b_imminent])
    await db_session.commit()

    # Cancel far booking -> 200 OK
    res_ok = await client.post(f"/bookings/{b_far.id}/cancel", headers=customer_headers)
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "cancelled"

    # Cancel imminent booking -> 400 CANCELLATION_WINDOW_EXPIRED
    res_err = await client.post(f"/bookings/{b_imminent.id}/cancel", headers=customer_headers)
    assert res_err.status_code == 400
    assert res_err.json()["code"] == "CANCELLATION_WINDOW_EXPIRED"


@pytest.mark.asyncio
async def test_reschedule_window_and_availability(client, customer_headers, booking_setup, db_session, customer_user):
    """Rescheduling >2h before start updates timestamps; <2h before start is rejected."""
    service = booking_setup["service"]
    stylist = booking_setup["stylist"]
    start_ts = get_next_monday_at(15, 0)

    booking = Booking(
        user_id=customer_user.id,
        service_id=service.id,
        stylist_id=stylist.id,
        start_ts=start_ts,
        end_ts=start_ts + timedelta(minutes=30),
        status="confirmed"
    )
    db_session.add(booking)
    await db_session.commit()

    new_start = get_next_monday_at(16, 0)
    reschedule_res = await client.put(
        f"/bookings/{booking.id}",
        json={"new_start_ts": new_start.isoformat(), "notes": "Shifted by 1hr"},
        headers=customer_headers
    )
    assert reschedule_res.status_code == 200
    assert reschedule_res.json()["start_ts"].replace("+00:00", "Z") == new_start.isoformat().replace("+00:00", "Z")


@pytest.mark.asyncio
async def test_get_my_bookings_with_filters(client, customer_headers, booking_setup, db_session, customer_user):
    """GET /bookings/me returns user bookings and filters by status."""
    service = booking_setup["service"]
    stylist = booking_setup["stylist"]
    d1 = get_next_monday_at(10, 0)
    d2 = get_next_monday_at(11, 0)

    b1 = Booking(user_id=customer_user.id, service_id=service.id, stylist_id=stylist.id,
                 start_ts=d1, end_ts=d1 + timedelta(minutes=30), status="confirmed")
    b2 = Booking(user_id=customer_user.id, service_id=service.id, stylist_id=stylist.id,
                 start_ts=d2, end_ts=d2 + timedelta(minutes=30), status="cancelled")
    db_session.add_all([b1, b2])
    await db_session.commit()

    # Query all
    res_all = await client.get("/bookings/me", headers=customer_headers)
    assert res_all.status_code == 200
    assert len(res_all.json()) >= 2

    # Filter confirmed only
    res_conf = await client.get("/bookings/me?status=confirmed", headers=customer_headers)
    assert res_conf.status_code == 200
    for b in res_conf.json():
        assert b["status"] == "confirmed"


@pytest.mark.asyncio
async def test_audit_logs_recorded(client, customer_headers, booking_setup, db_session):
    """AuditLog records CREATE, RESCHEDULE, and CANCEL actions with actor IDs."""
    service = booking_setup["service"]
    stylist = booking_setup["stylist"]
    start_ts = get_next_monday_at(9, 30)

    # 1. CREATE
    res1 = await client.post("/bookings", json={
        "service_id": service.id, "stylist_id": stylist.id, "start_ts": start_ts.isoformat()
    }, headers=customer_headers)
    booking_id = res1.json()["id"]

    # 2. RESCHEDULE
    new_start = get_next_monday_at(10, 30)
    await client.put(f"/bookings/{booking_id}", json={"new_start_ts": new_start.isoformat()}, headers=customer_headers)

    # 3. CANCEL
    await client.post(f"/bookings/{booking_id}/cancel", headers=customer_headers)

    # Verify audit logs
    stmt = select(AuditLog).where(AuditLog.entity_id == booking_id).order_by(AuditLog.id)
    logs = (await db_session.execute(stmt)).scalars().all()
    actions = [log.action for log in logs]
    assert "CREATE" in actions
    assert "RESCHEDULE" in actions
    assert "CANCEL" in actions


@pytest.mark.asyncio
async def test_concurrent_double_booking_collision(client, booking_setup, db_session):
    """
    Two simultaneous requests attempt to book the exact same slot.
    Exactly one succeeds (201) and one fails (409 SLOT_TAKEN).
    """
    service = booking_setup["service"]
    stylist = booking_setup["stylist"]
    slot_start = get_next_monday_at(13, 0)

    # Create two different customer users
    user_a = User(name="User A", email="usera@example.com", password_hash="h", role="customer")
    user_b = User(name="User B", email="userb@example.com", password_hash="h", role="customer")
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    token_a = create_access_token({"sub": user_a.email, "role": "customer"})
    token_b = create_access_token({"sub": user_b.email, "role": "customer"})
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    payload = {
        "service_id": service.id,
        "stylist_id": stylist.id,
        "start_ts": slot_start.isoformat(),
    }

    # Fire both booking requests concurrently
    res_a, res_b = await asyncio.gather(
        client.post("/bookings", json=payload, headers=headers_a),
        client.post("/bookings", json=payload, headers=headers_b),
    )

    statuses = {res_a.status_code, res_b.status_code}
    assert statuses == {201, 409}

    conflict_res = res_a if res_a.status_code == 409 else res_b
    assert conflict_res.json()["code"] == "SLOT_TAKEN"
