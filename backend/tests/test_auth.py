# Why: Tests for authentication endpoints: registration, login, and /auth/me.
# Covers duplicate registration (409), wrong password (401), token validation, and error shape.

import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    """Registering a new customer returns 201 with access token and user profile."""
    payload = {
        "name": "Sarah Connor",
        "email": "sarah@example.com",
        "phone": "+1-555-4321",
        "password": "Password123!",
        "role": "customer",
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "sarah@example.com"
    assert data["user"]["role"] == "customer"


@pytest.mark.asyncio
async def test_duplicate_registration_returns_409(client):
    """Registering with an already existing email returns 409 Conflict with code EMAIL_EXISTS."""
    payload = {
        "name": "First User",
        "email": "duplicate@example.com",
        "password": "Password123!",
    }
    # 1. First registration succeeds
    res1 = await client.post("/auth/register", json=payload)
    assert res1.status_code == 201

    # 2. Duplicate registration fails with 409
    res2 = await client.post("/auth/register", json=payload)
    assert res2.status_code == 409
    data = res2.json()
    assert data["code"] == "EMAIL_EXISTS"
    assert "already exists" in data["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(client):
    """Logging in with valid credentials returns 200 with JWT access token."""
    # Register first
    await client.post("/auth/register", json={
        "name": "Login User",
        "email": "loginuser@example.com",
        "password": "SecretPassword123!",
    })

    # Login
    login_res = await client.post("/auth/login", json={
        "email": "loginuser@example.com",
        "password": "SecretPassword123!",
    })
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "loginuser@example.com"


@pytest.mark.asyncio
async def test_wrong_password_returns_401(client):
    """Logging in with an incorrect password returns 401 Unauthorized with code INVALID_CREDENTIALS."""
    # Register first
    await client.post("/auth/register", json={
        "name": "Test User",
        "email": "wrongpass@example.com",
        "password": "CorrectPassword123!",
    })

    # Try login with wrong password
    response = await client.post("/auth/login", json={
        "email": "wrongpass@example.com",
        "password": "TotallyWrongPassword!",
    })
    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "INVALID_CREDENTIALS"
    assert "invalid email or password" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_current_user_me(client, customer_headers, customer_user):
    """GET /auth/me returns the profile of the authenticated user."""
    response = await client.get("/auth/me", headers=customer_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == customer_user.email
    assert data["name"] == customer_user.name
    assert data["role"] == "customer"


@pytest.mark.asyncio
async def test_get_me_without_token_returns_401(client):
    """Accessing /auth/me without an Authorization header returns 401."""
    response = await client.get("/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_register_invalid_phone_pattern(client):
    """Phone validation rejects malformed phone strings with 422."""
    payload = {
        "name": "Bad Phone",
        "email": "badphone@example.com",
        "phone": "not-a-phone-number",
        "password": "Password123!",
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"

