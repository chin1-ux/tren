import pytest


@pytest.mark.anyio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


@pytest.mark.anyio
async def test_root_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_trends_endpoint_exists(client):
    resp = await client.get("/api/trends")
    assert resp.status_code in (200, 401, 403, 500)


@pytest.mark.anyio
async def test_trends_emerging_exists(client):
    resp = await client.get("/api/trends/emerging")
    assert resp.status_code in (200, 401, 403)


@pytest.mark.anyio
async def test_trends_rising_exists(client):
    resp = await client.get("/api/trends/rising")
    assert resp.status_code in (200, 401, 403, 422)


@pytest.mark.anyio
async def test_trends_peak_exists(client):
    resp = await client.get("/api/trends/peak")
    assert resp.status_code in (200, 401, 403, 422)


@pytest.mark.anyio
async def test_trends_peaked_exists(client):
    resp = await client.get("/api/trends/peaked")
    assert resp.status_code in (200, 401, 403, 500)


@pytest.mark.anyio
async def test_trends_expired_exists(client):
    resp = await client.get("/api/trends/expired")
    assert resp.status_code in (200, 401, 403, 500)


@pytest.mark.anyio
async def test_trends_all_active_exists(client):
    resp = await client.get("/api/trends/all-active")
    assert resp.status_code in (200, 401, 403)


@pytest.mark.anyio
async def test_login_invalid_credentials(client):
    resp = await client.post("/api/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "wrongpassword"
    })
    assert resp.status_code in (401, 403, 422)


@pytest.mark.anyio
async def test_login_missing_fields(client):
    resp = await client.post("/api/auth/login", json={})
    assert resp.status_code in (401, 422)


@pytest.mark.anyio
async def test_signup_missing_fields(client):
    resp = await client.post("/api/auth/signup", json={})
    assert resp.status_code in (400, 422)


@pytest.mark.anyio
async def test_verify_no_token(client):
    resp = await client.post("/api/auth/verify", json={})
    assert resp.status_code in (401, 422)
