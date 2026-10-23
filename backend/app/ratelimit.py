import logging
import time

from fastapi import HTTPException, Request, status
from redis.exceptions import RedisError

from app.redis_client import redis
from app.tracking import client_ip

log = logging.getLogger(__name__)


async def hit(key: str, limit: int, window: int = 60) -> int | None:
    """Fixed-window counter. Returns seconds to wait if over the limit, else None."""
    now = time.time()
    bucket = int(now // window)
    redis_key = f"rl:{key}:{bucket}"
    try:
        async with redis.pipeline(transaction=True) as pipe:
            pipe.incr(redis_key)
            pipe.expire(redis_key, window, nx=True)
            count, _ = await pipe.execute()
    except RedisError:
        # Fail open: a cache outage shouldn't take logins and link creation down with it.
        log.warning("redis unavailable for rate limiting", exc_info=True)
        return None
    if count > limit:
        return max(1, int((bucket + 1) * window - now))
    return None


async def enforce(key: str, limit: int, window: int = 60) -> None:
    retry_after = await hit(key, limit, window)
    if retry_after is not None:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many requests, slow down",
            headers={"Retry-After": str(retry_after)},
        )


def ip_key(request: Request, name: str) -> str:
    return f"{name}:ip:{client_ip(request)}"
