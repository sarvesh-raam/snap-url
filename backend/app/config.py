from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://snapurl:snapurl@localhost:55432/snapurl"
    redis_url: str = "redis://localhost:56379/0"

    # Public origin that short links are served from, e.g. https://snap.example.com
    base_url: str = "http://localhost:8000"
    cors_origins: list[str] = ["http://localhost:5173"]

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    cookie_secure: bool = False

    code_length: int = 7
    link_cache_ttl: int = 3600
    negative_cache_ttl: int = 60

    # Click pipeline (Redis Stream -> worker -> Postgres)
    click_stream: str = "clicks"
    click_group: str = "click-writers"
    click_stream_maxlen: int = 1_000_000
    worker_batch_size: int = 500
    worker_block_ms: int = 1000
    worker_reclaim_idle_ms: int = 60_000

    # Rate limits (requests per window)
    rate_limit_create_per_min: int = 30
    rate_limit_login_per_min: int = 10

    # Client IP / country detection
    trust_proxy_headers: bool = False
    geoip_db_path: str | None = None

    # 0 = unlimited. A public demo caps this so the domain can't be mass-used for spam links.
    max_links_per_user: int = 0
    db_pool_size: int = 10

    environment: str = "development"

    def check_production(self) -> None:
        if self.environment != "production":
            return
        if len(self.jwt_secret) < 32 or self.jwt_secret in ("change-me", "dev-only-secret-change-me-in-production"):
            raise RuntimeError("JWT_SECRET must be set to a random value of at least 32 characters in production")
        if not self.base_url.startswith("https://"):
            raise RuntimeError("BASE_URL must be https:// in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
