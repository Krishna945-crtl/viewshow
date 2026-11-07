from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CV_", extra="ignore")

    app_name: str = "CineVerse 3D"
    env: str = "dev"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cineverse"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me-in-production-please-32b"
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
    mock_payment_secret: str = "mock-sandbox-secret"

    ticket_signing_secret: str = "ticket-secret-change-me"
    cors_origins: str = "http://localhost:3000,capacitor://localhost,http://localhost"
    sweeper_interval_seconds: float = 2.0
    run_sweeper: bool = True
    # auth abuse limits (per IP). raise them for load/e2e runs
    register_limit_per_hour: int = 10
    login_limit_per_5min: int = 20

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

    @property
    def tmdb_enabled(self) -> bool:
        return bool(self.tmdb_api_key or self.tmdb_read_token)

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
