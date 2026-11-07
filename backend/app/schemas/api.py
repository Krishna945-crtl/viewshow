from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

HEX_PATTERN = r"^#[0-9a-fA-F]{6}$"


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)
    city: str | None = Field(default=None, max_length=80)

    @field_validator("password")
    @classmethod
    def strong_enough(cls, v: str) -> str:
        if v.isdigit() or v.isalpha():
            raise ValueError("use letters and numbers")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    full_name: str
    city: str | None
    is_admin: bool


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class ProfileIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    city: str | None = Field(default=None, max_length=80)


class MovieIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9-]{1,120}$")
    tagline: str | None = Field(default=None, max_length=300)
    synopsis: str = Field(default="", max_length=5000)
    genres: list[str] = Field(default_factory=list, max_length=8)
    mood_tags: list[str] = Field(default_factory=list, max_length=12)
    palette_hint: list[str] = Field(default_factory=list, max_length=3)
    language: str = "English"
    certificate: str = Field(default="UA", max_length=8)
    runtime_minutes: int = Field(default=120, ge=1, le=600)
    release_date: date | None = None
    rating: float | None = Field(default=None, ge=0, le=10)
    poster_url: str | None = Field(default=None, max_length=500)
    backdrop_url: str | None = Field(default=None, max_length=500)
    trailer_url: str | None = Field(default=None, max_length=500)
    cast: list[str] = Field(default_factory=list, max_length=20)
    is_active: bool = True
    theme_id: str | None = None

    @field_validator("palette_hint")
    @classmethod
    def hexes(cls, v: list[str]) -> list[str]:
        import re
        for c in v:
            if not re.match(HEX_PATTERN, c):
                raise ValueError(f"{c} is not a #rrggbb colour")
        return v

    @field_validator("trailer_url", "poster_url", "backdrop_url")
    @classmethod
    def https_only(cls, v: str | None) -> str | None:
        if v and not (v.startswith("https://") or v.startswith("/")):
            raise ValueError("use an https:// or site-relative url")
        return v


class ThemeIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    config: dict


class ThemePreviewIn(BaseModel):
    title: str = "Untitled"
    tagline: str | None = None
    synopsis: str = ""
    genres: list[str] = []
    mood_tags: list[str] = []
    palette_hint: list[str] = []


class TheatreIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    city: str = Field(min_length=1, max_length=80)
    address: str = Field(default="", max_length=300)
    amenities: list[str] = []


class AuditoriumIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    layout: dict
    dimensions_verified: bool = False


class ShowIn(BaseModel):
    movie_id: str
    auditorium_id: str
    starts_at: datetime
    format: str = Field(default="2D", max_length=24)
    language: str = "English"
    prices: dict[str, int]  # category -> paise

    @field_validator("prices")
    @classmethod
    def sane_prices(cls, v: dict[str, int]) -> dict[str, int]:
        for k, p in v.items():
            if k not in {"standard", "premium", "recliner", "vip"}:
                raise ValueError(f"unknown category {k}")
            if p < 0 or p > 10_000_00:
                raise ValueError("price out of range")
        return v


class HoldIn(BaseModel):
    seat_ids: list[str] = Field(min_length=1, max_length=10)


class BookingIn(BaseModel):
    show_id: str
    seat_ids: list[str] = Field(min_length=1, max_length=10)


class OrderIn(BaseModel):
    booking_id: str


class VerifyIn(BaseModel):
    booking_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class MockCheckoutIn(BaseModel):
    order_id: str
    outcome: str = Field(default="success", pattern="^(success|failure)$")


class RecommendIn(BaseModel):
    group_size: int = Field(default=2, ge=1, le=10)
    max_price_per_seat: int | None = Field(default=None, ge=0)
    categories: list[str] = []


class TicketCheckIn(BaseModel):
    payload: str
