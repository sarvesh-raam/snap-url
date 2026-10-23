"""Click ingestion: enqueue on redirect, batch-write from the worker.

Delivery from the Redis Stream is at-least-once (a worker can crash after writing a
batch but before XACK). Writes are still counted exactly once: each click row is keyed
by its stream entry ID, and click_count is incremented only for rows the INSERT
actually created, in the same statement.
"""

import json
import logging
import uuid

from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import tracking
from app.config import get_settings
from app.db import SessionLocal
from app.redis_client import redis

log = logging.getLogger(__name__)

INSERT_CLICKS = text(
    """
    WITH ins AS (
        INSERT INTO clicks (event_id, link_id, clicked_at, country, device, browser, os,
                            referrer, visitor_hash, is_bot)
        SELECT r.event_id, r.link_id, r.clicked_at, r.country, r.device, r.browser, r.os,
               r.referrer, r.visitor_hash, r.is_bot
        FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS r(
            event_id text, link_id bigint, clicked_at timestamptz, country text, device text,
            browser text, os text, referrer text, visitor_hash text, is_bot boolean)
        JOIN links l ON l.id = r.link_id          -- drop events for links deleted meanwhile
        ON CONFLICT (event_id) DO NOTHING          -- redelivered events become no-ops
        RETURNING link_id, is_bot
    ), counts AS (
        SELECT link_id, count(*) AS n FROM ins WHERE NOT is_bot GROUP BY link_id
    ), bump AS (
        UPDATE links SET click_count = links.click_count + counts.n
        FROM counts WHERE links.id = counts.link_id
        RETURNING 1
    )
    SELECT (SELECT count(*) FROM ins) AS inserted, (SELECT count(*) FROM bump) AS links_bumped
    """
)


async def enqueue(event: dict[str, str]) -> None:
    s = get_settings()
    try:
        await redis.xadd(s.click_stream, event, maxlen=s.click_stream_maxlen, approximate=True)
    except RedisError:
        # Redis is down: write this one click straight to Postgres instead of losing it.
        log.warning("redis unavailable, writing click directly", exc_info=True)
        async with SessionLocal() as session:
            await write_batch(session, [(f"direct-{uuid.uuid4().hex[:24]}", event)])
            await session.commit()


async def write_batch(session: AsyncSession, messages: list[tuple[str, dict[str, str]]]) -> int:
    """Enriches and inserts a batch. Returns the number of new rows (duplicates excluded)."""
    rows = []
    for event_id, fields in messages:
        try:
            rows.append(tracking.enrich(event_id, fields))
        except (KeyError, ValueError):
            log.error("dropping malformed click event %s: %r", event_id, fields)
    if not rows:
        return 0
    payload = json.dumps(rows, default=lambda v: v.isoformat())
    result = await session.execute(INSERT_CLICKS, {"rows": payload})
    return result.one().inserted
