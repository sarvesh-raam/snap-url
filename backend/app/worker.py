"""Click worker: consumes the Redis Stream with a consumer group and batch-writes to Postgres.

Run with `python -m app.worker`. Several workers can run at once; the consumer group
gives each entry to exactly one of them, and entries a crashed worker never ACKed are
reclaimed with XAUTOCLAIM after `worker_reclaim_idle_ms`.
"""

import asyncio
import logging
import os
import signal
import socket
import time

from redis.exceptions import RedisError, ResponseError

from app.clicks import write_batch
from app.config import get_settings
from app.db import SessionLocal
from app.redis_client import redis

log = logging.getLogger("snapurl.worker")

RECLAIM_EVERY_S = 30


async def ensure_group() -> None:
    s = get_settings()
    try:
        # "0" rather than "$": events queued before the first worker starts are still processed.
        await redis.xgroup_create(s.click_stream, s.click_group, id="0", mkstream=True)
    except ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


async def handle(messages: list[tuple[str, dict[str, str]]]) -> int:
    if not messages:
        return 0
    s = get_settings()
    async with SessionLocal() as session:
        inserted = await write_batch(session, messages)
        await session.commit()
    # ACK only after the commit; a crash in between means redelivery, which is harmless.
    await redis.xack(s.click_stream, s.click_group, *[mid for mid, _ in messages])
    return inserted


async def reclaim(consumer: str) -> int:
    s = get_settings()
    total, cursor = 0, "0-0"
    while True:
        cursor, claimed, *_ = await redis.xautoclaim(
            s.click_stream, s.click_group, consumer, s.worker_reclaim_idle_ms, cursor, count=s.worker_batch_size
        )
        # Entries trimmed from the stream come back as None; ACK them so they leave the PEL.
        live = [(mid, f) for mid, f in claimed if f]
        dead = [mid for mid, f in claimed if not f]
        if dead:
            await redis.xack(s.click_stream, s.click_group, *dead)
        total += await handle(live)
        if cursor == "0-0":
            return total


async def run(stop: asyncio.Event) -> None:
    s = get_settings()
    consumer = f"{socket.gethostname()}-{os.getpid()}"
    await ensure_group()
    log.info("worker %s consuming %s as group %s", consumer, s.click_stream, s.click_group)
    last_reclaim = 0.0
    while not stop.is_set():
        try:
            if time.monotonic() - last_reclaim > RECLAIM_EVERY_S:
                if n := await reclaim(consumer):
                    log.info("reclaimed and wrote %d stale clicks", n)
                last_reclaim = time.monotonic()
            resp = await redis.xreadgroup(
                s.click_group, consumer, {s.click_stream: ">"}, count=s.worker_batch_size, block=s.worker_block_ms
            )
            for _stream, messages in resp or []:
                n = await handle(messages)
                log.info("wrote %d/%d clicks", n, len(messages))
        except (RedisError, OSError):
            log.exception("redis error; retrying in 2s")
            await asyncio.sleep(2)
        except Exception:
            # A database error leaves the batch un-ACKed; it is retried via reclaim.
            log.exception("batch failed; will be retried after reclaim idle time")
            await asyncio.sleep(2)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    async def _main() -> None:
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop.set)
            except NotImplementedError:  # Windows
                pass
        await run(stop)

    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
