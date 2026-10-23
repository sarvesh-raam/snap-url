import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://snapurl:snapurl@localhost:55432/snapurl_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:56379/15")
os.environ["BASE_URL"] = "http://sn.test"
os.environ["TRUST_PROXY_HEADERS"] = "true"
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret"
os.environ["ENVIRONMENT"] = "test"
os.environ["RATE_LIMIT_LOGIN_PER_MIN"] = "1000"
os.environ["RATE_LIMIT_CREATE_PER_MIN"] = "1000"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import models  # noqa: E402,F401
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.redis_client import redis  # noqa: E402


def pytest_collection_modifyitems(items):
    # The engine and Redis pools are module globals bound to one event loop; share it.
    session_loop = pytest.mark.asyncio(loop_scope="session")
    for item in items:
        if isinstance(item, pytest.Function) and item.get_closest_marker("asyncio"):
            item.add_marker(session_loop, append=False)


@pytest.fixture(scope="session", autouse=True)
async def schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean():
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE clicks, links, refresh_tokens, users RESTART IDENTITY CASCADE"))
    await redis.flushdb()
    yield


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://sn.test") as c:
        yield c


async def signup(client: AsyncClient, email: str = "a@example.com", password: str = "password123") -> dict:
    r = await client.post("/api/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def auth(client):
    return await signup(client)
