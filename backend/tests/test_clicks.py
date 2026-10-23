from sqlalchemy import text

from app import worker
from app.clicks import write_batch
from app.config import get_settings
from app.db import SessionLocal, engine
from app.redis_client import redis
from tests.test_units import CHROME_WIN, GOOGLEBOT, SAFARI_IPHONE

S = get_settings()


async def drain(consumer: str = "test") -> int:
    await worker.ensure_group()
    total = 0
    while True:
        resp = await redis.xreadgroup(S.click_group, consumer, {S.click_stream: ">"}, count=100, block=None)
        if not resp:
            return total
        for _stream, messages in resp:
            total += await worker.handle(messages)


async def make_link(client, auth, alias="promo"):
    r = await client.post("/api/links", json={"url": "https://example.com", "alias": alias}, headers=auth)
    return r.json()


async def visit(client, code, ua, ip, country="", ref=""):
    headers = {"user-agent": ua, "x-forwarded-for": ip}
    if country:
        headers["cf-ipcountry"] = country
    if ref:
        headers["referer"] = ref
    assert (await client.get(f"/{code}", headers=headers)).status_code == 302


async def test_end_to_end_analytics(client, auth):
    link = await make_link(client, auth)
    await visit(client, "promo", CHROME_WIN, "8.8.8.8", "US", "https://www.google.com/search?q=x")
    await visit(client, "promo", CHROME_WIN, "8.8.8.8", "US", "https://www.google.com/search?q=y")  # same visitor
    await visit(client, "promo", SAFARI_IPHONE, "1.1.1.1", "IN", "https://t.co/abc")
    await visit(client, "promo", SAFARI_IPHONE, "9.9.9.9", "IN")
    await visit(client, "promo", GOOGLEBOT, "66.249.66.1", "US")

    assert await drain() == 5

    stats = (await client.get(f"/api/links/{link['id']}/stats?days=7", headers=auth)).json()
    assert stats["total_clicks"] == 4  # bot excluded
    assert stats["bot_clicks"] == 1
    assert stats["unique_visitors"] == 3
    assert len(stats["timeseries"]) == 7 and stats["timeseries"][-1]["clicks"] == 4
    assert {r["key"]: r["count"] for r in stats["countries"]} == {"US": 2, "IN": 2}
    assert {r["key"]: r["count"] for r in stats["devices"]} == {"desktop": 2, "mobile": 2}
    assert {r["key"]: r["count"] for r in stats["referrers"]} == {"google.com": 2, "t.co": 1, "Direct": 1}
    assert {r["key"] for r in stats["browsers"]} == {"Chrome", "Mobile Safari"}

    detail = (await client.get(f"/api/links/{link['id']}", headers=auth)).json()
    assert detail["click_count"] == 4

    overview = (await client.get("/api/stats/overview?days=7", headers=auth)).json()
    assert overview["total_clicks"] == 4 and overview["clicks_last_7d"] == 4
    assert overview["top_links"][0]["code"] == "promo"


async def test_redelivered_batch_is_counted_once(client, auth):
    link = await make_link(client, auth)
    await visit(client, "promo", CHROME_WIN, "8.8.8.8")
    messages = await redis.xrange(S.click_stream)

    async with SessionLocal() as session:
        assert await write_batch(session, messages) == 1
        await session.commit()
    # Simulates a worker that committed but crashed before XACK: the batch comes back.
    async with SessionLocal() as session:
        assert await write_batch(session, messages) == 0
        await session.commit()

    detail = (await client.get(f"/api/links/{link['id']}", headers=auth)).json()
    assert detail["click_count"] == 1


async def test_crashed_consumer_entries_are_reclaimed(client, auth, monkeypatch):
    await make_link(client, auth)
    await worker.ensure_group()
    await visit(client, "promo", CHROME_WIN, "8.8.8.8")
    # Consumer "dead" reads the entry and never ACKs it.
    await redis.xreadgroup(S.click_group, "dead", {S.click_stream: ">"}, count=10)
    assert (await redis.xpending(S.click_stream, S.click_group))["pending"] == 1

    monkeypatch.setattr(S, "worker_reclaim_idle_ms", 0)
    assert await worker.reclaim("alive") == 1
    assert (await redis.xpending(S.click_stream, S.click_group))["pending"] == 0


async def test_events_for_deleted_links_are_dropped(client, auth):
    link = await make_link(client, auth)
    await visit(client, "promo", CHROME_WIN, "8.8.8.8")
    await client.delete(f"/api/links/{link['id']}", headers=auth)
    assert await drain() == 0
    assert (await redis.xpending(S.click_stream, S.click_group))["pending"] == 0


async def test_malformed_events_are_skipped(client, auth):
    link = await make_link(client, auth)
    await visit(client, "promo", CHROME_WIN, "8.8.8.8")
    await redis.xadd(S.click_stream, {"garbage": "1"})
    assert await drain() == 1
    async with engine.connect() as conn:
        n = await conn.scalar(text("SELECT count(*) FROM clicks WHERE link_id = :id"), {"id": link["id"]})
    assert n == 1
