# Why: Tests for the 5-minute pre-booking slot hold mechanism.
# Validates hold creation, early manual release, isolation between customers,
# hold conversion into booking, expiry reappearance, and APScheduler DB cleanup.

from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy import select

from app.core.security import create_access_token
from app.jobs.cleanup_holds import delete_expired_holds
from app.models import Service, Stylist, stylist_services, WorkingHours, SlotHold, User


@pytest.fixture
async def hold_setup(db_session):
    """Sets up a test service and stylist with upcoming Monday working hours."""
    service = Service(
        name="Express Haircut",
        category="Hair",
        duration_min=30,
        price=Decimal("35.00"),
        is_active=True,
    )
    stylist = Stylist(name="Sam Stylist", specialization="Cuts", is_active=True)
    db_session.add_all([service, stylist])
    await db_session.flush()

    await db_session.execute(
        stylist_services.insert().values(stylist_id=stylist.id, service_id=service.id)
    )

    wh = WorkingHours(stylist_id=stylist.id, weekday=0, start_time=time(9, 0), end_time=time(18, 0))
    db_session.add(wh)

    user_a = User(name="Customer A", email="usera@test.com", password_hash="h", role="customer")
    user_b = User(name="Customer B", email="userb@test.com", password_hash="h", role="customer")
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    token_a = create_access_token({"sub": user_a.email, "role": "customer"})
    token_b = create_access_token({"sub": user_b.email, "role": "customer"})

    return {
        "service": service,
        "stylist": stylist,
        "user_a": user_a,
        "user_b": user_b,
        "headers_a": {"Authorization": f"Bearer {token_a}"},
        "headers_b": {"Authorization": f"Bearer {token_b}"},
    }


def get_next_monday_at(hour: int, minute: int = 0) -> datetime:
    today = datetime.now(timezone.utc).date()
    days_ahead = (0 - today.weekday()) % 7 or 7
    return datetime.combine(today + timedelta(days=days_ahead), time(hour, minute), tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_create_and_delete_hold(client, hold_setup):
    """Customer can reserve a 5-minute hold and manually release it."""
    service = hold_setup["service"]
    stylist = hold_setup["stylist"]
    start_ts = get_next_monday_at(10, 0)

    # 1. POST /holds
    res = await client.post("/holds", json={
        "service_id": service.id,
        "stylist_id": stylist.id,
        "start_ts": start_ts.isoformat(),
    }, headers=hold_setup["headers_a"])
    assert res.status_code == 201
    hold_data = res.json()
    assert hold_data["stylist_id"] == stylist.id
    assert "expires_at" in hold_data
    hold_id = hold_data["id"]

    # 2. DELETE /holds/{id}
    del_res = await client.delete(f"/holds/{hold_id}", headers=hold_setup["headers_a"])
    assert del_res.status_code == 200
    assert del_res.json()["code"] == "HOLD_RELEASED"


@pytest.mark.asyncio
async def test_user_b_cannot_see_held_slot(client, hold_setup):
    """When user A holds a slot, it is hidden from GET /slots for all users."""
    service = hold_setup["service"]
    stylist = hold_setup["stylist"]
    slot_time = get_next_monday_at(11, 0)
    target_date = slot_time.date().isoformat()

    # User A holds 11:00 slot
    await client.post("/holds", json={
        "service_id": service.id,
        "stylist_id": stylist.id,
        "start_ts": slot_time.isoformat(),
    }, headers=hold_setup["headers_a"])

    # User B queries available slots
    slots_res = await client.get(
        f"/slots?service_id={service.id}&date={target_date}&stylist_id={stylist.id}&lead_time_min=0",
        headers=hold_setup["headers_b"]
    )
    assert slots_res.status_code == 200
    available_starts = [s["start_ts"] for s in slots_res.json()]
    assert slot_time.isoformat().replace("+00:00", "Z") not in available_starts


@pytest.mark.asyncio
async def test_user_b_cannot_book_held_slot(client, hold_setup):
    """User B cannot book a slot currently held by user A (409 SLOT_HELD)."""
    service = hold_setup["service"]
    stylist = hold_setup["stylist"]
    slot_time = get_next_monday_at(12, 0)

    # User A holds slot
    await client.post("/holds", json={
        "service_id": service.id,
        "stylist_id": stylist.id,
        "start_ts": slot_time.isoformat(),
    }, headers=hold_setup["headers_a"])

    # User B attempts to book the same slot
    book_res = await client.post("/bookings", json={
        "service_id": service.id,
        "stylist_id": stylist.id,
        "start_ts": slot_time.isoformat(),
    }, headers=hold_setup["headers_b"])
    assert book_res.status_code == 409
    assert book_res.json()["code"] == "SLOT_HELD"


@pytest.mark.asyncio
async def test_user_a_can_convert_hold_to_booking(client, hold_setup, db_session):
    """User A can pass hold_id to POST /bookings to convert their hold into a confirmed booking."""
    service = hold_setup["service"]
    stylist = hold_setup["stylist"]
    slot_time = get_next_monday_at(14, 0)

    # 1. Hold
    h_res = await client.post("/holds", json={
        "service_id": service.id,
        "stylist_id": stylist.id,
        "start_ts": slot_time.isoformat(),
    }, headers=hold_setup["headers_a"])
    hold_id = h_res.json()["id"]

    # 2. Convert hold into booking
    b_res = await client.post("/bookings", json={
        "service_id": service.id,
        "stylist_id": stylist.id,
        "start_ts": slot_time.isoformat(),
        "hold_id": hold_id,
        "notes": "Converted from active hold",
    }, headers=hold_setup["headers_a"])
    assert b_res.status_code == 201
    assert b_res.json()["status"] == "confirmed"

    # 3. Verify hold was purged from DB
    remaining_hold = (await db_session.execute(select(SlotHold).where(SlotHold.id == hold_id))).scalar_one_or_none()
    assert remaining_hold is None


@pytest.mark.asyncio
async def test_slot_reappears_after_expiry(client, hold_setup, db_session):
    """Slot engine ignores expired holds at read time, making slot available again."""
    service = hold_setup["service"]
    stylist = hold_setup["stylist"]
    slot_time = get_next_monday_at(15, 0)
    target_date = slot_time.date().isoformat()
    now_utc = datetime.now(timezone.utc)

    # Insert an expired hold directly into DB (expired 1 minute ago)
    expired_hold = SlotHold(
        user_id=hold_setup["user_a"].id,
        stylist_id=stylist.id,
        start_ts=slot_time,
        end_ts=slot_time + timedelta(minutes=30),
        expires_at=now_utc - timedelta(minutes=1),  # Already expired
    )
    db_session.add(expired_hold)
    await db_session.commit()

    # User B queries slots -> expired hold must be ignored!
    res = await client.get(
        f"/slots?service_id={service.id}&date={target_date}&stylist_id={stylist.id}&lead_time_min=0",
        headers=hold_setup["headers_b"]
    )
    assert res.status_code == 200
    slot_starts = [s["start_ts"] for s in res.json()]
    assert slot_time.isoformat().replace("+00:00", "Z") in slot_starts

    # User B can now book the slot
    book_res = await client.post("/bookings", json={
        "service_id": service.id,
        "stylist_id": stylist.id,
        "start_ts": slot_time.isoformat(),
    }, headers=hold_setup["headers_b"])
    assert book_res.status_code == 201


@pytest.mark.asyncio
async def test_apscheduler_cleanup_purges_only_expired_holds(db_session, hold_setup):
    """delete_expired_holds purges past holds while leaving active holds intact."""
    stylist = hold_setup["stylist"]
    user_a = hold_setup["user_a"]
    now_utc = datetime.now(timezone.utc)

    # 1. Expired hold
    h_exp = SlotHold(
        user_id=user_a.id,
        stylist_id=stylist.id,
        start_ts=get_next_monday_at(16, 0),
        end_ts=get_next_monday_at(16, 30),
        expires_at=now_utc - timedelta(minutes=2),
    )
    # 2. Active hold
    h_act = SlotHold(
        user_id=user_a.id,
        stylist_id=stylist.id,
        start_ts=get_next_monday_at(17, 0),
        end_ts=get_next_monday_at(17, 30),
        expires_at=now_utc + timedelta(minutes=5),
    )
    db_session.add_all([h_exp, h_act])
    await db_session.commit()

    # Run cleanup job
    deleted_count = await delete_expired_holds(db_session)
    assert deleted_count == 1

    # Verify active hold remains
    remaining = (await db_session.execute(select(SlotHold))).scalars().all()
    assert len(remaining) == 1
    assert remaining[0].id == h_act.id
