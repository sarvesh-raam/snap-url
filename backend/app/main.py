import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from sqlalchemy import text

from app.config import get_settings
from app.db import engine
from app.redis_client import redis
from app.routers import analytics, auth, links, redirect

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await redis.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    s = get_settings()
    s.check_production()
    app = FastAPI(
        title="SnapURL",
        version="1.0.0",
        description="URL shortener with click analytics.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["ops"])
    async def health() -> JSONResponse:
        checks = {}
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["postgres"] = "ok"
        except Exception:
            checks["postgres"] = "down"
        try:
            await redis.ping()
            checks["redis"] = "ok"
        except RedisError:
            checks["redis"] = "degraded"  # redirects still work from Postgres
        healthy = checks["postgres"] == "ok"
        return JSONResponse({"status": "ok" if healthy else "down", **checks}, status_code=200 if healthy else 503)

    app.include_router(auth.router)
    app.include_router(links.router)
    app.include_router(analytics.router)
    # Last: its catch-all /{code} must not shadow the routes above.
    app.include_router(redirect.router)
    return app


app = create_app()
