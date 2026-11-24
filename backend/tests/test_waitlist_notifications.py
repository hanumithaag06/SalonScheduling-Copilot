# Why: Integration tests for the waitlist and notification systems.
# Validates: joining, duplicate guard, cascade on cancellation, 15-min offer,
# claiming, offer expiry + cascade to next customer, and in-app notifications.

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import pytest

from app.models import Service, Stylist, stylist_services, WorkingHours, Booking, User, Waitlist
from app.core.security import hash_password, create_access_token
from app.services.email_service import sent_emails_log, clear_sent_emails_log


def get_next_monday() -> date:
    today = datetime.now(timezone.utc).date()
    days_ahead = (0 - today.weekday()) % 7 or 7
    return today + timedelta(days=days_ahead)


@pytest.fixture(autouse=True)
def reset_email_log():
    """Clears the in-memory email log before each test."""
    clear_sent_emails_log()


@pytest.fixture
async def waitlist_data(db_session):
    """Sets up two customers, a service, two stylists, and working hours."""
    cust_a = User(
        name="Anna Waiting",
        email="anna.waitlist@example.com",
        phone="+12025550201",
        password_hash=hash_password("pass123"),
        role="customer",
    )
    cust_b = User(
        name="Brad Waiting",
        email="brad.waitlist@example.com",
        phone="+12025550202",
        password_hash=hash_password("pass123"),
        role="customer",
    )
    db_session.add_all([cust_a, cust_b])
    await db_session.flush()

    service = Service(
        name="Precision Haircut",
        category="Hair",
        duration_min=30,
        price=Decimal("40.00"),
        is_active=True,
    )
    db_session.add(service)
    await db_session.flush()

    stylist = Stylist(name="Carol Cut", specialization="Haircuts", is_active=True)
    db_session.add(stylist)
    await db_session.flush()

    await db_session.execute(
        stylist_services.insert(),
        [{"stylist_id": stylist.id, "service_id": service.id}],
    )

    # Working hours: Monday
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
        "cust_a": cust_a,
        "cust_b": cust_b,
        "service": service,
        "stylist": stylist,
    }


@pytest.mark.asyncio
async def test_join_waitlist_success(client, waitlist_data):
    """POST /waitlist creates a 'waiting' entry for a valid future date and service."""
    data = waitlist_data
    target = get_next_monday().isoformat()
    token = create_access_token({"sub": data["cust_a"].email, "role": "customer"})

    resp = await client.post(
        "/waitlist",
        json={"service_id": data["service"].id, "date": target, "time_pref": "morning"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "waiting"
    assert body["service_id"] == data["service"].id


@pytest.mark.asyncio
async def test_join_waitlist_duplicate_blocked(client, waitlist_data):
    """A second POST /waitlist for the same service+date returns 409 ALREADY_ON_WAITLIST."""
    data = waitlist_data
    target = get_next_monday().isoformat()
    token = create_access_token({"sub": data["cust_a"].email, "role": "customer"})
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(
        "/waitlist",
        json={"service_id": data["service"].id, "date": target, "time_pref": "any"},
        headers=headers,
    )
    resp2 = await client.post(
        "/waitlist",
        json={"service_id": data["service"].id, "date": target, "time_pref": "any"},
        headers=headers,
    )
    assert resp2.status_code == 409
    assert resp2.json()["code"] == "ALREADY_ON_WAITLIST"


@pytest.mark.asyncio
async def test_cancellation_triggers_waitlist_offer(client, waitlist_data, db_session):
    """
    Cancelling a confirmed booking offers the vacated slot to the first
    matching waitlisted customer and sends a notification + email.
    """
    data = waitlist_data
    target_monday = get_next_monday()
    slot_start = datetime(target_monday.year, target_monday.month, target_monday.day, 10, 0, tzinfo=timezone.utc)
    slot_end = slot_start + timedelta(minutes=30)

    # 1. Register cust_b on the waitlist for morning slot
    entry = Waitlist(
        user_id=data["cust_b"].id,
        service_id=data["service"].id,
        stylist_id=None,  # any stylist
        date=target_monday,
        time_pref="morning",
        status="waiting",
    )
    db_session.add(entry)

    # 2. Create a confirmed booking for cust_a at 10:00
    booking = Booking(
        user_id=data["cust_a"].id,
        service_id=data["service"].id,
        stylist_id=data["stylist"].id,
        start_ts=slot_start,
        end_ts=slot_end,
        status="confirmed",
    )
    db_session.add(booking)
    await db_session.commit()

    # 3. Cancel the booking via API (must be > 2h before slot; use future slot that is far enough)
    token_a = create_access_token({"sub": data["cust_a"].email, "role": "customer"})
    cancel_resp = await client.post(
        f"/bookings/{booking.id}/cancel",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # 4. Verify waitlist entry is now 'offered' with a slot time and expiry
    await db_session.refresh(entry)
    assert entry.status == "offered"
    assert entry.offered_slot_start is not None
    assert entry.offer_expires_at is not None

    # 5. Verify an email was sent to cust_b
    matching_emails = [e for e in sent_emails_log if data["cust_b"].email in e["to"]]
    assert len(matching_emails) >= 1
    assert "Slot Available" in matching_emails[0]["subject"]


@pytest.mark.asyncio
async def test_claim_waitlist_offer(client, waitlist_data, db_session):
    """POST /waitlist/{id}/claim within 15 min creates a confirmed booking and marks entry 'claimed'."""
    data = waitlist_data
    target_monday = get_next_monday()
    slot_start = datetime(target_monday.year, target_monday.month, target_monday.day, 14, 0, tzinfo=timezone.utc)

    # Create a pre-offered waitlist entry for cust_a
    entry = Waitlist(
        user_id=data["cust_a"].id,
        service_id=data["service"].id,
        stylist_id=data["stylist"].id,
        date=target_monday,
        time_pref="afternoon",
        status="offered",
        offered_slot_start=slot_start,
        offer_expires_at=datetime.now(timezone.utc) + timedelta(minutes=14),  # 14 minutes remaining
    )
    db_session.add(entry)
    await db_session.commit()

    token_a = create_access_token({"sub": data["cust_a"].email, "role": "customer"})
    resp = await client.post(
        f"/waitlist/{entry.id}/claim",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "claimed"


@pytest.mark.asyncio
async def test_expired_offer_cascades_to_next(client, waitlist_data, db_session):
    """
    When a customer does not claim within 15 minutes, claiming returns 409 OFFER_EXPIRED
    and the slot cascades to the next waiting customer.
    """
    data = waitlist_data
    target_monday = get_next_monday()
    slot_start = datetime(target_monday.year, target_monday.month, target_monday.day, 11, 0, tzinfo=timezone.utc)

    # cust_a has an EXPIRED offer
    expired_entry = Waitlist(
        user_id=data["cust_a"].id,
        service_id=data["service"].id,
        stylist_id=data["stylist"].id,
        date=target_monday,
        time_pref="any",
        status="offered",
        offered_slot_start=slot_start,
        offer_expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),  # already expired
    )
    # cust_b is next in line
    next_entry = Waitlist(
        user_id=data["cust_b"].id,
        service_id=data["service"].id,
        stylist_id=None,
        date=target_monday,
        time_pref="any",
        status="waiting",
    )
    db_session.add_all([expired_entry, next_entry])
    await db_session.commit()

    token_a = create_access_token({"sub": data["cust_a"].email, "role": "customer"})
    resp = await client.post(
        f"/waitlist/{expired_entry.id}/claim",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    # 409 expected since offer expired
    assert resp.status_code == 409
    assert resp.json()["code"] == "OFFER_EXPIRED"

    # Verify cust_b is now 'offered'
    await db_session.refresh(next_entry)
    assert next_entry.status == "offered"
    assert next_entry.offered_slot_start is not None


@pytest.mark.asyncio
async def test_get_my_notifications(client, waitlist_data, db_session):
    """GET /notifications returns in-app notifications for the authenticated user."""
    from app.models import Notification
    data = waitlist_data

    # Seed an in-app notification for cust_a
    notif = Notification(
        user_id=data["cust_a"].id,
        type="booking_confirmed",
        message="Your booking is confirmed!",
        channel="in_app",
        status="unread",
    )
    db_session.add(notif)
    await db_session.commit()

    token_a = create_access_token({"sub": data["cust_a"].email, "role": "customer"})
    resp = await client.get("/notifications", headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    assert items[0]["type"] == "booking_confirmed"
    assert items[0]["status"] == "unread"


@pytest.mark.asyncio
async def test_mark_notification_read(client, waitlist_data, db_session):
    """POST /notifications/{id}/read flips status to 'read'."""
    from app.models import Notification
    data = waitlist_data

    notif = Notification(
        user_id=data["cust_a"].id,
        type="reminder_24h",
        message="Reminder: 24 hours to your appointment!",
        channel="in_app",
        status="unread",
    )
    db_session.add(notif)
    await db_session.commit()

    token_a = create_access_token({"sub": data["cust_a"].email, "role": "customer"})
    resp = await client.post(
        f"/notifications/{notif.id}/read",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "read"
