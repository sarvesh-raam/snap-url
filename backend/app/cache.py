"""Cache-aside for the redirect hot path. Redis failures degrade to Postgres, never to errors."""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from redis.exceptions import RedisError

from app.config import get_settings
from app.redis_client import redis

log = logging.getLogger(__name__)

_MISSING = ""  # negative-cache marker for codes that don't exist


@dataclass
class CachedLink:
    id: int
    url: str
    active: bool
    expires_at: str | None  # ISO-8601

    def is_live(self) -> bool:
        if not self.active:
            return False
        return self.expires_at is None or datetime.fromisoformat(self.expires_at) > datetime.now(UTC)


def _key(code: str) -> str:
    return f"link:{code}"


async def get(code: str) -> CachedLink | None | bool:
    """Returns a CachedLink on hit, False if the code is known not to exist, None on miss."""
    try:
        raw = await redis.get(_key(code))
    except RedisError:
        log.warning("redis unavailable for cache read", exc_info=True)
        return None
    if raw is None:
        return None
    if raw == _MISSING:
        return False
    return CachedLink(**json.loads(raw))


async def put(code: str, link: CachedLink | None) -> None:
    s = get_settings()
    try:
        if link is None:
            await redis.set(_key(code), _MISSING, ex=s.negative_cache_ttl)
        else:
            await redis.set(_key(code), json.dumps(asdict(link)), ex=s.link_cache_ttl)
    except RedisError:
        log.warning("redis unavailable for cache write", exc_info=True)


async def invalidate(code: str) -> None:
    try:
        await redis.delete(_key(code))
    except RedisError:
        log.warning("redis unavailable for cache invalidation of %s", code, exc_info=True)
