# Why: Tests for admin-only CRUD operations: services, stylists, mappings,
# working hours, and time-off. Verifies 403 FORBIDDEN for customers and Pydantic validations.

from datetime import datetime, timezone, timedelta, time
import pytest


@pytest.mark.asyncio
async def test_customer_cannot_create_service_returns_403(client, customer_headers):
    """Customer attempting an admin-only route returns 403 Forbidden with code FORBIDDEN."""
    payload = {
        "name": "Unauthorized Service",
        "category": "Hair",
        "duration_min": 30,
        "price": 40.0,
    }
    response = await client.post("/services", json=payload, headers=customer_headers)
    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "FORBIDDEN"
    assert "admin" in data["detail"].lower()


@pytest.mark.asyncio
async def test_admin_service_crud_lifecycle(client, admin_headers):
    """Admin can create, list, retrieve, update, and soft-delete services."""
    # 1. Create
    payload = {
        "name": "Luxury Beard Treatment",
        "category": "Hair",
        "duration_min": 45,
        "price": 50.00,
        "is_active": True,
    }
    create_res = await client.post("/services", json=payload, headers=admin_headers)
    assert create_res.status_code == 201
    service_id = create_res.json()["id"]

    # 2. Get
    get_res = await client.get(f"/services/{service_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Luxury Beard Treatment"

    # 3. Update
    update_res = await client.put(
        f"/services/{service_id}",
        json={"price": 60.00, "name": "Royal Beard Treatment"},
        headers=admin_headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["price"] == "60.00"
    assert update_res.json()["name"] == "Royal Beard Treatment"

    # 4. Soft-delete
    del_res = await client.delete(f"/services/{service_id}", headers=admin_headers)
    assert del_res.status_code == 200
    assert del_res.json()["code"] == "SERVICE_DEACTIVATED"

    # Active-only list should exclude it
    list_res = await client.get("/services?active_only=true")
    ids = [s["id"] for s in list_res.json()]
    assert service_id not in ids


@pytest.mark.asyncio
async def test_service_validation_duration_and_price(client, admin_headers):
    """Validates that duration must be > 0 and price must be >= 0."""
    # Duration <= 0 rejected
    res1 = await client.post("/services", json={
        "name": "Zero Duration",
        "category": "Hair",
        "duration_min": 0,
        "price": 20.0,
    }, headers=admin_headers)
    assert res1.status_code == 422
    assert res1.json()["code"] == "VALIDATION_ERROR"

    # Price < 0 rejected
    res2 = await client.post("/services", json={
        "name": "Negative Price",
        "category": "Hair",
        "duration_min": 30,
        "price": -15.0,
    }, headers=admin_headers)
    assert res2.status_code == 422
    assert res2.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_admin_stylist_and_service_mapping(client, admin_headers):
    """Admin creates a stylist and assigns services."""
    # 1. Create a service first
    s_res = await client.post("/services", json={
        "name": "Balayage", "category": "Color", "duration_min": 90, "price": 120.0
    }, headers=admin_headers)
    service_id = s_res.json()["id"]

    # 2. Create stylist with service
    st_res = await client.post("/stylists", json={
        "name": "Giselle",
        "specialization": "Color Expert",
        "service_ids": [service_id],
    }, headers=admin_headers)
    assert st_res.status_code == 201
    stylist_id = st_res.json()["id"]
    assert len(st_res.json()["services"]) == 1

    # 3. Re-assign services
    assign_res = await client.post(
        f"/stylists/{stylist_id}/services",
        json={"service_ids": [service_id]},
        headers=admin_headers
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["services"][0]["id"] == service_id


@pytest.mark.asyncio
async def test_admin_working_hours_and_time_off(client, admin_headers, customer_headers):
    """Admin configures stylist working hours and time-off, validates permissions and time ranges."""
    # Create a stylist
    st_res = await client.post("/stylists", json={
        "name": "Chloe", "specialization": "Styling"
    }, headers=admin_headers)
    stylist_id = st_res.json()["id"]

    # 1. Set Working Hours (Mon: 09:00 - 17:00)
    wh_res = await client.post(
        f"/stylists/{stylist_id}/working-hours",
        json={"weekday": 0, "start_time": "09:00:00", "end_time": "17:00:00"},
        headers=admin_headers
    )
    assert wh_res.status_code == 201
    assert wh_res.json()["weekday"] == 0

    # 2. Reject Working Hours where end <= start
    bad_wh = await client.post(
        f"/stylists/{stylist_id}/working-hours",
        json={"weekday": 1, "start_time": "17:00:00", "end_time": "09:00:00"},
        headers=admin_headers
    )
    assert bad_wh.status_code == 422

    # 3. Create Time Off
    now = datetime.now(timezone.utc)
    to_res = await client.post(
        f"/stylists/{stylist_id}/time-off",
        json={
            "start_ts": (now + timedelta(days=5)).isoformat(),
            "end_ts": (now + timedelta(days=7)).isoformat(),
            "reason": "Annual Holiday",
        },
        headers=admin_headers
    )
    assert to_res.status_code == 201
    assert to_res.json()["reason"] == "Annual Holiday"

    # 4. Customer blocked from adding time-off
    blocked_to = await client.post(
        f"/stylists/{stylist_id}/time-off",
        json={
            "start_ts": (now + timedelta(days=1)).isoformat(),
            "end_ts": (now + timedelta(days=2)).isoformat(),
            "reason": "Not allowed",
        },
        headers=customer_headers
    )
    assert blocked_to.status_code == 403
    assert blocked_to.json()["code"] == "FORBIDDEN"

