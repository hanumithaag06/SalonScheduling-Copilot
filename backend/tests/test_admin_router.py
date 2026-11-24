# Why: Integration tests for the admin dashboard, calendar queries, CSV export,
# proxy booking/cancellation, and verification that dashboard totals match seed data.

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import io
import csv
import pytest

from app.models import Service, Stylist, stylist_services, WorkingHours, Booking, User, AuditLog
from app.core.security import hash_password, create_access_token
from seed import seed_data


def get_next_monday() -> date:
    today = datetime.now(timezone.utc).date()
    days_ahead = (0 - today.weekday()) % 7 or 7
    return today + timedelta(days=days_ahead)


@pytest.fixture
async def setup_admin_test_env(db_session):
    """Sets up an admin, a customer, a stylist, a service, and shifts."""
    admin = User(
        name="Admin Chief",
        email="chief.admin@stylify.com",
        phone="+12025550001",
        password_hash=hash_password("adminpass"),
        role="admin",
    )
    customer = User(
        name="Sam Customer",
        email="sam.client@example.com",
        phone="+12025550002",
        password_hash=hash_password("custpass"),
        role="customer",
    )
    service = Service(
        name="Deluxe Cut & Style",
        category="Hair",
        duration_min=45,
        price=Decimal("50.00"),
        is_active=True,
    )
    stylist = Stylist(
        name="Sasha Hair",
        specialization="Haircuts & Styling",
        is_active=True,
    )
    db_session.add_all([admin, customer, service, stylist])
    await db_session.flush()

    await db_session.execute(
        stylist_services.insert(),
        [{"stylist_id": stylist.id, "service_id": service.id}],
    )

    # Shift: Monday 09:00 - 17:00
    target_monday = get_next_monday()
    wh = WorkingHours(
        stylist_id=stylist.id,
        weekday=target_monday.weekday(),
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    db_session.add(wh)
    await db_session.commit()

    return {
        "admin": admin,
        "customer": customer,
        "service": service,
        "stylist": stylist,
    }


@pytest.mark.asyncio
async def test_customer_forbidden_on_admin_routes(client, setup_admin_test_env):
    """Customers receive 403 Forbidden on all /admin endpoints."""
    data = setup_admin_test_env
    cust_token = create_access_token({"sub": data["customer"].email, "role": "customer"})
    headers = {"Authorization": f"Bearer {cust_token}"}

    # GET /admin/bookings
    resp1 = await client.get("/admin/bookings", headers=headers)
    assert resp1.status_code == 403
    assert resp1.json()["code"] == "FORBIDDEN"

    # GET /admin/dashboard
    resp2 = await client.get("/admin/dashboard", headers=headers)
    assert resp2.status_code == 403

    # GET /admin/export/bookings.csv
    resp3 = await client.get("/admin/export/bookings.csv", headers=headers)
    assert resp3.status_code == 403

    # POST /admin/bookings
    resp4 = await client.post("/admin/bookings", json={}, headers=headers)
    assert resp4.status_code == 403


@pytest.mark.asyncio
async def test_admin_list_bookings_with_filters(client, setup_admin_test_env, db_session):
    """Admin can list and filter bookings by date range, stylist, and status."""
    data = setup_admin_test_env
    admin_token = create_access_token({"sub": data["admin"].email, "role": "admin"})
    headers = {"Authorization": f"Bearer {admin_token}"}
    target_monday = get_next_monday()

    # Create 2 bookings with different statuses
    b1 = Booking(
        user_id=data["customer"].id,
        service_id=data["service"].id,
        stylist_id=data["stylist"].id,
        start_ts=datetime(target_monday.year, target_monday.month, target_monday.day, 10, 0, tzinfo=timezone.utc),
        end_ts=datetime(target_monday.year, target_monday.month, target_monday.day, 10, 45, tzinfo=timezone.utc),
        status="confirmed",
        notes="First VIP booking",
    )
    b2 = Booking(
        user_id=data["customer"].id,
        service_id=data["service"].id,
        stylist_id=data["stylist"].id,
        start_ts=datetime(target_monday.year, target_monday.month, target_monday.day, 12, 0, tzinfo=timezone.utc),
        end_ts=datetime(target_monday.year, target_monday.month, target_monday.day, 12, 45, tzinfo=timezone.utc),
        status="cancelled",
        notes="Second cancelled booking",
    )
    db_session.add_all([b1, b2])
    await db_session.commit()

    # Query all
    resp = await client.get("/admin/bookings", headers=headers)
    assert resp.status_code == 200
    all_bks = resp.json()
    assert len(all_bks) == 2
    assert all_bks[0]["user_email"] == data["customer"].email

    # Filter by status = confirmed
    resp_conf = await client.get("/admin/bookings?status=confirmed", headers=headers)
    assert resp_conf.status_code == 200
    assert len(resp_conf.json()) == 1
    assert resp_conf.json()[0]["status"] == "confirmed"

    # Filter by stylist_id
    resp_st = await client.get(f"/admin/bookings?stylist_id={data['stylist'].id}", headers=headers)
    assert resp_st.status_code == 200
    assert len(resp_st.json()) == 2


@pytest.mark.asyncio
async def test_admin_dashboard_totals_match_seed(client, db_session):
    """
    Seeds demo data into the test database and verifies that GET /admin/dashboard
    totals strictly match the seed dataset.
    """
    seed_result = await seed_data(db_session)
    total_seeded_bookings = seed_result["bookings"]
    assert total_seeded_bookings > 50

    # Retrieve seeded admin user for auth
    admin_token = create_access_token({"sub": "admin@stylify.com", "role": "admin"})
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Query dashboard over a wide window encompassing all 60 seeded days
    today = datetime.now(timezone.utc).date()
    p_from = (today - timedelta(days=90)).isoformat()
    p_to = (today + timedelta(days=30)).isoformat()

    response = await client.get(f"/admin/dashboard?from={p_from}&to={p_to}", headers=headers)
    assert response.status_code == 200
    data = response.json()

    # 1. Total bookings match seeded count
    assert data["total_bookings"] == total_seeded_bookings

    # 2. Status sum integrity
    status_sum = data["confirmed_bookings"] + data["cancelled_bookings"] + data["completed_bookings"]
    assert status_sum == data["total_bookings"]

    # 3. Revenue is calculated and non-zero
    assert float(data["total_revenue"]) > 0

    # 4. Cancellation rate percentage is realistic
    assert 0.0 <= data["cancellation_rate_pct"] <= 100.0

    # 5. Bookings per day populated
    assert len(data["bookings_per_day"]) > 0
    total_bpd = sum(item["count"] for item in data["bookings_per_day"])
    assert total_bpd == total_seeded_bookings

    # 6. Revenue per service covers seeded services
    assert len(data["revenue_per_service"]) == 10

    # 7. Stylist utilization computed for all 5 seeded stylists
    assert len(data["stylist_utilization"]) == 5
    for util in data["stylist_utilization"]:
        assert 0.0 <= util["utilization_pct"] <= 100.0

    # 8. Peak hours and heatmap present
    assert len(data["peak_hours"]) <= 5
    assert len(data["heatmap"]) > 0


@pytest.mark.asyncio
async def test_admin_export_bookings_csv(client, setup_admin_test_env, db_session):
    """Admin can export bookings as a valid CSV attachment."""
    data = setup_admin_test_env
    admin_token = create_access_token({"sub": data["admin"].email, "role": "admin"})
    headers = {"Authorization": f"Bearer {admin_token}"}
    target_monday = get_next_monday()

    # Add sample booking
    b = Booking(
        user_id=data["customer"].id,
        service_id=data["service"].id,
        stylist_id=data["stylist"].id,
        start_ts=datetime(target_monday.year, target_monday.month, target_monday.day, 10, 0, tzinfo=timezone.utc),
        end_ts=datetime(target_monday.year, target_monday.month, target_monday.day, 10, 45, tzinfo=timezone.utc),
        status="confirmed",
        notes="CSV test booking",
    )
    db_session.add(b)
    await db_session.commit()

    resp = await client.get("/admin/export/bookings.csv", headers=headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert 'attachment; filename="bookings.csv"' in resp.headers["content-disposition"]

    # Parse and verify CSV contents
    reader = csv.reader(io.StringIO(resp.text))
    rows = list(reader)
    header = rows[0]
    assert "booking_id" in header
    assert "customer_email" in header
    assert "service_name" in header
    assert "status" in header

    # Verify at least 1 data row exists
    assert len(rows) >= 2
    data_row = rows[1]
    assert data["customer"].email in data_row


@pytest.mark.asyncio
async def test_admin_create_booking_proxy(client, setup_admin_test_env, db_session):
    """Admin can book an appointment on behalf of a customer."""
    data = setup_admin_test_env
    admin_token = create_access_token({"sub": data["admin"].email, "role": "admin"})
    headers = {"Authorization": f"Bearer {admin_token}"}
    target_monday = get_next_monday()
    start_dt = datetime(target_monday.year, target_monday.month, target_monday.day, 11, 0, tzinfo=timezone.utc)

    payload = {
        "user_id": data["customer"].id,
        "service_id": data["service"].id,
        "stylist_id": data["stylist"].id,
        "start_ts": start_dt.isoformat(),
        "notes": "Booked by front desk admin",
    }

    resp = await client.post("/admin/bookings", json=payload, headers=headers)
    assert resp.status_code == 201
    booking_data = resp.json()
    assert booking_data["user_id"] == data["customer"].id
    assert booking_data["status"] == "confirmed"
    assert booking_data["notes"] == "Booked by front desk admin"

    # Verify AuditLog recorded action ADMIN_CREATE
    from sqlalchemy import select
    audit_stmt = select(AuditLog).where(AuditLog.action == "ADMIN_CREATE")
    audit = (await db_session.execute(audit_stmt)).scalar_one_or_none()
    assert audit is not None
    assert audit.actor_id == data["admin"].id


@pytest.mark.asyncio
async def test_admin_cancel_booking_proxy(client, setup_admin_test_env, db_session):
    """Admin can cancel a customer's booking regardless of ownership."""
    data = setup_admin_test_env
    admin_token = create_access_token({"sub": data["admin"].email, "role": "admin"})
    headers = {"Authorization": f"Bearer {admin_token}"}
    target_monday = get_next_monday()

    # Customer's booking
    b = Booking(
        user_id=data["customer"].id,
        service_id=data["service"].id,
        stylist_id=data["stylist"].id,
        start_ts=datetime(target_monday.year, target_monday.month, target_monday.day, 14, 0, tzinfo=timezone.utc),
        end_ts=datetime(target_monday.year, target_monday.month, target_monday.day, 14, 45, tzinfo=timezone.utc),
        status="confirmed",
    )
    db_session.add(b)
    await db_session.commit()

    resp = await client.post(f"/admin/bookings/{b.id}/cancel", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    # Verify AuditLog recorded action ADMIN_CANCEL
    from sqlalchemy import select
    audit_stmt = select(AuditLog).where(AuditLog.action == "ADMIN_CANCEL")
    audit = (await db_session.execute(audit_stmt)).scalar_one_or_none()
    assert audit is not None
    assert audit.actor_id == data["admin"].id
