# Why: Integration tests for the GET /slots endpoint.
# Verifies database constraint assembly, filtering (stylist_id, max_price),
# active hold suppression, and 404 behavior for unknown services.

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import pytest
from app.models import Service, Stylist, stylist_services, WorkingHours, SlotHold, User


def get_next_monday_iso() -> str:
    """Returns the ISO string for the next upcoming Monday so tests are always in the future."""
    today = datetime.now(timezone.utc).date()
    days_ahead = (0 - today.weekday()) % 7 or 7
    return (today + timedelta(days=days_ahead)).isoformat()


@pytest.fixture
async def setup_slot_data(db_session):
    """Sets up a service, two stylists with shifts, and mappings."""
    # 1. Services
    service = Service(
        name="Precision Haircut",
        category="Hair",
        duration_min=30,
        price=Decimal("40.00"),
        is_active=True,
    )
    db_session.add(service)
    await db_session.flush()

    # 2. Stylists
    stylist_a = Stylist(name="Alice Hair", specialization="Hair Specialist", is_active=True)
    stylist_b = Stylist(name="Bob Barber", specialization="Barbering", is_active=True)
    db_session.add_all([stylist_a, stylist_b])
    await db_session.flush()

    # 3. Associate both stylists with the service
    await db_session.execute(
        stylist_services.insert(),
        [
            {"stylist_id": stylist_a.id, "service_id": service.id},
            {"stylist_id": stylist_b.id, "service_id": service.id},
        ]
    )

    # 4. Working hours: Monday (0) 09:00 - 17:00 for both
    wh_a = WorkingHours(stylist_id=stylist_a.id, weekday=0, start_time=time(9, 0), end_time=time(17, 0))
    wh_b = WorkingHours(stylist_id=stylist_b.id, weekday=0, start_time=time(9, 0), end_time=time(17, 0))
    db_session.add_all([wh_a, wh_b])
    await db_session.commit()

    return {
        "service": service,
        "stylist_a": stylist_a,
        "stylist_b": stylist_b,
    }


@pytest.mark.asyncio
async def test_get_slots_success(client, setup_slot_data):
    """GET /slots returns 200 with available slots on a valid future working weekday."""
    service_id = setup_slot_data["service"].id
    target_date = get_next_monday_iso()

    response = await client.get(f"/slots?service_id={service_id}&date={target_date}&lead_time_min=0")
    assert response.status_code == 200
    slots = response.json()
    assert len(slots) > 0
    first_slot = slots[0]
    assert first_slot["duration_min"] == 30
    assert first_slot["price"] == "40.00"
    assert "start_ts" in first_slot
    assert "end_ts" in first_slot


@pytest.mark.asyncio
async def test_get_slots_filtered_by_stylist(client, setup_slot_data):
    """GET /slots?stylist_id=... only returns slots belonging to the specified stylist."""
    service_id = setup_slot_data["service"].id
    stylist_a_id = setup_slot_data["stylist_a"].id
    target_date = get_next_monday_iso()

    response = await client.get(
        f"/slots?service_id={service_id}&date={target_date}&stylist_id={stylist_a_id}&lead_time_min=0"
    )
    assert response.status_code == 200
    slots = response.json()
    assert len(slots) > 0
    for s in slots:
        assert s["stylist_id"] == stylist_a_id


@pytest.mark.asyncio
async def test_get_slots_max_price_filter(client, setup_slot_data):
    """GET /slots with max_price lower than service price returns an empty list."""
    service_id = setup_slot_data["service"].id  # Price is 40.00
    target_date = get_next_monday_iso()

    # Budget 50.00 >= 40.00 -> returns slots
    res_ok = await client.get(
        f"/slots?service_id={service_id}&date={target_date}&max_price=50.00&lead_time_min=0"
    )
    assert res_ok.status_code == 200
    assert len(res_ok.json()) > 0

    # Budget 30.00 < 40.00 -> returns []
    res_under = await client.get(
        f"/slots?service_id={service_id}&date={target_date}&max_price=30.00&lead_time_min=0"
    )
    assert res_under.status_code == 200
    assert res_under.json() == []


@pytest.mark.asyncio
async def test_get_slots_unknown_service_returns_404(client):
    """GET /slots with non-existent service_id returns 404 with SERVICE_NOT_FOUND."""
    response = await client.get(f"/slots?service_id=999999&date={get_next_monday_iso()}")
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "SERVICE_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_slots_respects_active_slot_holds(client, db_session, setup_slot_data):
    """Active slot holds temporarily remove that interval from available slots."""
    service = setup_slot_data["service"]
    stylist_a = setup_slot_data["stylist_a"]

    # Create temporary user for the hold
    user = User(name="Hold Guy", email="holdguy@example.com", password_hash="hash", role="customer")
    db_session.add(user)
    await db_session.flush()

    # Place an active 5-minute hold on Stylist A on the upcoming Monday
    today = datetime.now(timezone.utc).date()
    days_ahead = (0 - today.weekday()) % 7 or 7
    target_mon = today + timedelta(days=days_ahead)

    hold_start = datetime.combine(target_mon, time(9, 0), tzinfo=timezone.utc)
    hold_end = datetime.combine(target_mon, time(9, 30), tzinfo=timezone.utc)
    hold = SlotHold(
        user_id=user.id,
        stylist_id=stylist_a.id,
        start_ts=hold_start,
        end_ts=hold_end,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),  # Active hold
    )
    db_session.add(hold)
    await db_session.commit()

    # Query Stylist A's slots
    response = await client.get(
        f"/slots?service_id={service.id}&date={target_mon.isoformat()}&stylist_id={stylist_a.id}&lead_time_min=0"
    )
    assert response.status_code == 200
    slots = response.json()

    # 09:00 - 09:30 must NOT be present
    slot_starts = [s["start_ts"] for s in slots]
    assert hold_start.isoformat().replace("+00:00", "Z") not in slot_starts
