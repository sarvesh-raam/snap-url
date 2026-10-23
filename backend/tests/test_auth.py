from tests.conftest import signup

COOKIE = "snapurl_refresh"


async def test_register_login_me(client):
    await signup(client, "Me@Example.com")
    r = await client.post("/api/auth/login", json={"email": "me@example.com", "password": "password123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "me@example.com"


async def test_duplicate_email_conflicts(client):
    await signup(client)
    r = await client.post("/api/auth/register", json={"email": "A@example.com", "password": "password123"})
    assert r.status_code == 409


async def test_wrong_password_and_unknown_email_look_the_same(client):
    await signup(client)
    wrong = await client.post("/api/auth/login", json={"email": "a@example.com", "password": "nope-nope"})
    unknown = await client.post("/api/auth/login", json={"email": "z@example.com", "password": "nope-nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


async def test_requires_token(client):
    assert (await client.get("/api/links")).status_code == 401
    assert (await client.get("/api/links", headers={"Authorization": "Bearer junk"})).status_code == 401


async def test_short_password_rejected(client):
    r = await client.post("/api/auth/register", json={"email": "a@example.com", "password": "short"})
    assert r.status_code == 422


async def test_refresh_rotates_token(client):
    await signup(client)
    first = client.cookies[COOKIE]
    r = await client.post("/api/auth/refresh")
    assert r.status_code == 200
    assert client.cookies[COOKIE] != first


async def test_reusing_rotated_refresh_token_revokes_the_family(client):
    await signup(client)
    stolen = client.cookies[COOKIE]
    assert (await client.post("/api/auth/refresh")).status_code == 200
    current = client.cookies[COOKIE]

    # Attacker replays the old token: rejected, and the legitimate session dies too.
    client.cookies.set(COOKIE, stolen, domain="sn.test", path="/api/auth")
    assert (await client.post("/api/auth/refresh")).status_code == 401
    client.cookies.set(COOKIE, current, domain="sn.test", path="/api/auth")
    assert (await client.post("/api/auth/refresh")).status_code == 401


async def test_logout_revokes_refresh_token(client):
    await signup(client)
    token = client.cookies[COOKIE]
    assert (await client.post("/api/auth/logout")).status_code == 204
    client.cookies.set(COOKIE, token, domain="sn.test", path="/api/auth")
    assert (await client.post("/api/auth/refresh")).status_code == 401


async def test_login_rate_limit(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "rate_limit_login_per_min", 3)
    codes = [
        (await client.post("/api/auth/login", json={"email": "x@example.com", "password": "password123"})).status_code
        for _ in range(4)
    ]
    assert codes == [401, 401, 401, 429]
