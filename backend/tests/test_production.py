import pytest

from app.config import Settings, get_settings


def test_production_refuses_default_secret_and_plain_http():
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        Settings(environment="production", jwt_secret="change-me", base_url="https://s.example").check_production()
    with pytest.raises(RuntimeError, match="https"):
        Settings(environment="production", jwt_secret="x" * 40, base_url="http://s.example").check_production()
    Settings(environment="production", jwt_secret="x" * 40, base_url="https://s.example").check_production()


async def test_link_cap_per_user(client, auth, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_links_per_user", 2)
    codes = [(await client.post("/api/links", json={"url": "example.com"}, headers=auth)).status_code for _ in range(3)]
    assert codes == [201, 201, 403]
