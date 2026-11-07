import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamped, utcnow


def new_id() -> str:
    return uuid.uuid4().hex


class SeatCategory(str, enum.Enum):
    standard = "standard"
    premium = "premium"
    recliner = "recliner"
    vip = "vip"


class BookingStatus(str, enum.Enum):
    pending = "PENDING_PAYMENT"
    confirmed = "CONFIRMED"
    cancelled = "CANCELLED"
    expired = "EXPIRED"
    failed = "FAILED"


class PaymentStatus(str, enum.Enum):
    created = "CREATED"
    captured = "CAPTURED"
    failed = "FAILED"
    refund_pending = "REFUND_PENDING"
    refunded = "REFUNDED"


def _enum(e):
    return Enum(e, native_enum=False, length=24, values_callable=lambda x: [m.value for m in x])


class User(Base, Timestamped):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    city: Mapped[str | None] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class RefreshToken(Base, Timestamped):
    __tablename__ = "refresh_tokens"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class MovieTheme(Base, Timestamped):
    """Admin-authored atmosphere. Movies without one get an auto-generated theme."""

    __tablename__ = "movie_themes"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    config: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Movie(Base, Timestamped):
    __tablename__ = "movies"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    tagline: Mapped[str | None] = mapped_column(String(300))
    synopsis: Mapped[str] = mapped_column(Text, default="")
    genres: Mapped[list] = mapped_column(JSON, default=list)
    # free-form mood words ("desert", "ocean", "neon"...) - feeds the theme engine
    mood_tags: Mapped[list] = mapped_column(JSON, default=list)
    # optional colours an admin picked off the key art, e.g. ["#1b3a6b", "#7fd3ff"]
    palette_hint: Mapped[list] = mapped_column(JSON, default=list)
    # TMDB-style keywords ("kaiju", "desert planet") - strong theme signals
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    # dominant colours pulled from an uploaded / imported poster: [{"hex", "weight"}]
    art_palette: Mapped[list] = mapped_column(JSON, default=list)
    # set when the movie was imported from TMDB, stops double imports
    tmdb_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    language: Mapped[str] = mapped_column(String(40), default="English")
    certificate: Mapped[str] = mapped_column(String(8), default="UA")
    runtime_minutes: Mapped[int] = mapped_column(Integer, default=120)
    release_date: Mapped[date | None] = mapped_column(Date)
    rating: Mapped[float | None] = mapped_column(Float)
    poster_url: Mapped[str | None] = mapped_column(String(500))
    backdrop_url: Mapped[str | None] = mapped_column(String(500))
    trailer_url: Mapped[str | None] = mapped_column(String(500))
    cast: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    theme_id: Mapped[str | None] = mapped_column(ForeignKey("movie_themes.id", ondelete="SET NULL"))
    theme: Mapped[MovieTheme | None] = relationship(lazy="joined")


class Theatre(Base, Timestamped):
    __tablename__ = "theatres"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160))
    city: Mapped[str] = mapped_column(String(80), index=True)
    address: Mapped[str] = mapped_column(String(300), default="")
    # we never pretend demo venues are real cinemas
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    amenities: Mapped[list] = mapped_column(JSON, default=list)
    auditoriums: Mapped[list["Auditorium"]] = relationship(back_populates="theatre", lazy="selectin")


class Auditorium(Base, Timestamped):
    __tablename__ = "auditoriums"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    theatre_id: Mapped[str] = mapped_column(ForeignKey("theatres.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    # raw layout as authored (rows/blocks/aisles/screen). seats are derived from it
    layout: Mapped[dict] = mapped_column(JSON)
    # true only when the dimensions came from real measurements
    dimensions_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    theatre: Mapped[Theatre] = relationship(back_populates="auditoriums", lazy="joined")
    __table_args__ = (UniqueConstraint("theatre_id", "name"),)


class Seat(Base):
    __tablename__ = "seats"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    auditorium_id: Mapped[str] = mapped_column(ForeignKey("auditoriums.id", ondelete="CASCADE"), index=True)
    row_label: Mapped[str] = mapped_column(String(4))
    number: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(8))
    category: Mapped[SeatCategory] = mapped_column(_enum(SeatCategory))
    block: Mapped[int] = mapped_column(Integer, default=0)
    # metres. x = across, y = up, z = distance back from the screen plane (z=0).
    # yaw = rotation about +Y; 0 means facing straight at the screen (-z)
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    z: Mapped[float] = mapped_column(Float)
    yaw: Mapped[float] = mapped_column(Float, default=0.0)
    grid_col: Mapped[int] = mapped_column(Integer)
    grid_row: Mapped[int] = mapped_column(Integer)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_accessible: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint("auditorium_id", "label"),)


class Show(Base, Timestamped):
    __tablename__ = "shows"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    movie_id: Mapped[str] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    auditorium_id: Mapped[str] = mapped_column(ForeignKey("auditoriums.id", ondelete="CASCADE"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    format: Mapped[str] = mapped_column(String(24), default="2D")
    language: Mapped[str] = mapped_column(String(40), default="English")
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    movie: Mapped[Movie] = relationship(lazy="joined")
    auditorium: Mapped[Auditorium] = relationship(lazy="joined")
    prices: Mapped[list["ShowPrice"]] = relationship(lazy="selectin", cascade="all, delete-orphan")


class ShowPrice(Base):
    __tablename__ = "show_prices"
    show_id: Mapped[str] = mapped_column(ForeignKey("shows.id", ondelete="CASCADE"), primary_key=True)
    category: Mapped[SeatCategory] = mapped_column(_enum(SeatCategory), primary_key=True)
    price_paise: Mapped[int] = mapped_column(Integer)


class Booking(Base, Timestamped):
    __tablename__ = "bookings"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    reference: Mapped[str] = mapped_column(String(12), unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    show_id: Mapped[str] = mapped_column(ForeignKey("shows.id"), index=True)
    status: Mapped[BookingStatus] = mapped_column(_enum(BookingStatus), default=BookingStatus.pending, index=True)
    amount_paise: Mapped[int] = mapped_column(Integer)
    convenience_fee_paise: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    seats: Mapped[list["BookingSeat"]] = relationship(lazy="selectin", cascade="all, delete-orphan")
    show: Mapped[Show] = relationship(lazy="joined")


class BookingSeat(Base):
    """One row per seat in a booking.

    `active` is the real double-booking guard: a partial unique index makes it
    impossible for two live bookings to own the same (show, seat) pair, no matter
    what happens in Redis or app code.
    """

    __tablename__ = "booking_seats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), index=True)
    show_id: Mapped[str] = mapped_column(ForeignKey("shows.id"))
    seat_id: Mapped[str] = mapped_column(ForeignKey("seats.id"))
    price_paise: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    seat: Mapped[Seat] = relationship(lazy="joined")
    __table_args__ = (
        Index(
            "uq_booking_seats_live",
            "show_id",
            "seat_id",
            unique=True,
            postgresql_where=text("active"),
        ),
    )


class Payment(Base, Timestamped):
    __tablename__ = "payments"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.id"), index=True)
    provider: Mapped[str] = mapped_column(String(20))
    provider_order_id: Mapped[str] = mapped_column(String(64), unique=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    amount_paise: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[PaymentStatus] = mapped_column(_enum(PaymentStatus), default=PaymentStatus.created)
    failure_reason: Mapped[str | None] = mapped_column(String(300))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WebhookEvent(Base, Timestamped):
    """Stored so a replayed webhook is a no-op."""

    __tablename__ = "webhook_events"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    provider: Mapped[str] = mapped_column(String(20))
    event_type: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict] = mapped_column(JSON)


class ErrorLog(Base, Timestamped):
    __tablename__ = "error_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(32))
    path: Mapped[str] = mapped_column(String(300))
    method: Mapped[str] = mapped_column(String(8))
    error_type: Mapped[str] = mapped_column(String(120))
    message: Mapped[str] = mapped_column(Text)
