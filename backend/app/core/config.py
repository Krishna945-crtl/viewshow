from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# defaults that are fine on a laptop and must never reach a public server
DEV_SECRETS = {
    "jwt_secret": "change-me-in-production-please-32b",
    "ticket_signing_secret": "ticket-secret-change-me",
    "mock_payment_secret": "mock-sandbox-secret",
    "seed_admin_password": "Admin@123",
}


def asyncpg_url(url: str) -> str:
    """Hosted Postgres (Neon, Render, Heroku...) hands out postgres://...?sslmode=require.
    asyncpg wants postgresql+asyncpg:// and calls the TLS flag `ssl`, and it has no channel_binding."""
    parts = urlsplit(url.strip())
    scheme = parts.scheme
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"
    query = []
    for k, v in parse_qsl(parts.query, keep_blank_values=True):
        if k == "sslmode":
            query.append(("ssl", v))
        elif k != "channel_binding":
            query.append((k, v))
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CV_", extra="ignore")

    app_name: str = "CineVerse 3D"
    env: str = "dev"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cineverse"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = DEV_SECRETS["jwt_secret"]
    access_token_minutes: int = 30
    refresh_token_days: int = 14

    # seat hold window (seconds). the brief says 5 min to start with
    hold_seconds: int = 300
    # how long a pending booking waits for payment before we let the seats go
    payment_window_seconds: int = 480
    max_seats_per_booking: int = 10

    # "mock" = local sandbox simulator, "razorpay" = Razorpay test mode
    payment_provider: str = "mock"
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    mock_payment_secret: str = DEV_SECRETS["mock_payment_secret"]

    ticket_signing_secret: str = DEV_SECRETS["ticket_signing_secret"]
    cors_origins: str = "http://localhost:3000,capacitor://localhost,http://localhost"
    sweeper_interval_seconds: float = 2.0
    run_sweeper: bool = True
    # auth abuse limits (per IP). raise them for load/e2e runs
    register_limit_per_hour: int = 10
    login_limit_per_5min: int = 20

    # password for the seeded admin account. the public demo user stays demo@cineverse.dev / Demo@1234
    seed_admin_password: str = DEV_SECRETS["seed_admin_password"]
    # built website (next export) to serve at / - lets one container host both site and API
    static_dir: str = ""

    # uploaded artwork (posters). local disk by default, served at /media
    media_dir: str = "media"
    max_upload_mb: int = 6
    art_preview_limit_per_10min: int = 30

    # optional: import any real movie from TMDB (https://www.themoviedb.org/settings/api)
    # either the v3 api key or the v4 read-access token works
    tmdb_api_key: str = ""
    tmdb_read_token: str = ""
    tmdb_language: str = "en-US"
    tmdb_region: str = "IN"  # which country's certificate (U / UA / A) to use
    # show TMDB poster images in the app (allowed by TMDB's API terms, with attribution).
    # false = only the poster's colours are used for the theme
    tmdb_show_posters: bool = True

    @field_validator("database_url")
    @classmethod
    def _asyncpg(cls, v: str) -> str:
        return asyncpg_url(v)

    @model_validator(mode="after")
    def _no_dev_secrets_in_prod(self):
        if self.env == "prod":
            left = [k for k, v in DEV_SECRETS.items() if getattr(self, k) == v or not getattr(self, k)]
            if left:
                # RuntimeError, not ValueError: pydantic would wrap a ValueError and echo every
                # setting (DB password included) into the logs
                raise RuntimeError("set these before running in prod: " + ", ".join(f"CV_{k.upper()}" for k in left))
        return self

    @property
    def tmdb_enabled(self) -> bool:
        return bool(self.tmdb_api_key or self.tmdb_read_token)

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
