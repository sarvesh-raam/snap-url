from sqlalchemy import text

from app.config import get_settings
from app.db import engine
from app.redis_client import redis


async def make(client, auth, **body):
    r = await client.post("/api/links", json={"url": "https://example.com/landing", **body}, headers=auth)
    assert r.status_code == 201, r.text
    return r.json()


async def test_redirects_with_302_and_no_store(client, auth):
    link = await make(client, auth)
    r = await client.get(f"/{link['code']}")
    assert r.status_code == 302
    assert r.headers["location"] == "https://example.com/landing"
    assert r.headers["cache-control"] == "private, no-store"


async def test_cache_is_populated_and_serves_without_db(client, auth):
    link = await make(client, auth, alias="cached")
    await client.get("/cached")
    assert await redis.get("link:cached") is not None
    # Change the row behind the cache's back: the cached target is still served.
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE links SET target_url = 'https://changed.com' WHERE id = :id"), {"id": link["id"]}
        )
    assert (await client.get("/cached")).headers["location"] == "https://example.com/landing"


async def test_update_invalidates_cache(client, auth):
    link = await make(client, auth, alias="moving")
    await client.get("/moving")
    await client.patch(f"/api/links/{link['id']}", json={"url": "https://moved.com"}, headers=auth)
    assert (await client.get("/moving")).headers["location"] == "https://moved.com"


async def test_unknown_code_is_negatively_cached_then_cleared_on_create(client, auth):
    assert (await client.get("/fresh")).status_code == 404
    assert await redis.get("link:fresh") == ""
    assert 0 < await redis.ttl("link:fresh") <= get_settings().negative_cache_ttl
    await make(client, auth, alias="fresh")
    assert (await client.get("/fresh")).status_code == 302


async def test_disabled_and_expired_links_return_410(client, auth):
    off = await make(client, auth, alias="off")
    await client.patch(f"/api/links/{off['id']}", json={"is_active": False}, headers=auth)
    assert (await client.get("/off")).status_code == 410

    old = await make(client, auth, alias="old")
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE links SET expires_at = now() - interval '1 minute' WHERE id = :id"), {"id": old["id"]}
        )
    assert (await client.get("/old")).status_code == 410


async def test_head_does_not_count_a_click(client, auth):
    link = await make(client, auth)
    assert (await client.head(f"/{link['code']}")).status_code == 302
    assert await redis.xlen(get_settings().click_stream) == 0
    await client.get(f"/{link['code']}")
    assert await redis.xlen(get_settings().click_stream) == 1


async def test_api_and_health_are_not_shadowed(client):
    assert (await client.get("/health")).json()["status"] == "ok"
    assert (await client.get("/api/links")).status_code == 401
