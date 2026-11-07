from app.core.security import ticket_payload
from app.models import Booking, Movie, Show
from app.services.theme_engine import resolve_theme


def movie_signals(m: Movie) -> dict:
    return {"title": m.title, "tagline": m.tagline, "synopsis": m.synopsis, "genres": m.genres,
            "mood_tags": m.mood_tags, "palette_hint": m.palette_hint}


def movie_out(m: Movie, full: bool = False) -> dict:
    theme = resolve_theme(movie_signals(m), m.theme.config if m.theme else None)
    if m.theme:
        theme["name"] = m.theme.name
    data = {
        "id": m.id, "slug": m.slug, "title": m.title, "tagline": m.tagline,
        "genres": m.genres, "language": m.language, "certificate": m.certificate,
        "runtime_minutes": m.runtime_minutes, "rating": m.rating,
        "release_date": m.release_date.isoformat() if m.release_date else None,
        "poster_url": m.poster_url, "backdrop_url": m.backdrop_url,
        "is_active": m.is_active, "theme": theme, "theme_id": m.theme_id,
    }
    if full:
        data |= {"synopsis": m.synopsis, "cast": m.cast, "trailer_url": m.trailer_url,
                 "mood_tags": m.mood_tags, "palette_hint": m.palette_hint}
    return data


def show_out(s: Show) -> dict:
    a = s.auditorium
    return {
        "id": s.id, "movie_id": s.movie_id, "starts_at": s.starts_at.isoformat(),
        "format": s.format, "language": s.language, "is_cancelled": s.is_cancelled,
        "auditorium": {"id": a.id, "name": a.name, "theatre_id": a.theatre_id},
        "prices": {p.category.value: p.price_paise for p in s.prices},
    }


def booking_out(b: Booking, with_ticket: bool = True) -> dict:
    s = b.show
    theatre = s.auditorium.theatre
    data = {
        "id": b.id, "reference": b.reference, "status": b.status.value,
        "amount_paise": b.amount_paise, "convenience_fee_paise": b.convenience_fee_paise,
        "expires_at": b.expires_at.isoformat(),
        "confirmed_at": b.confirmed_at.isoformat() if b.confirmed_at else None,
        "created_at": b.created_at.isoformat(),
        "checked_in_at": b.checked_in_at.isoformat() if b.checked_in_at else None,
        "seats": sorted(
            ({"id": x.seat_id, "label": x.seat.label, "category": x.seat.category.value, "price_paise": x.price_paise}
             for x in b.seats),
            key=lambda d: (d["label"][0], len(d["label"]), d["label"]),
        ),
        "show": {"id": s.id, "starts_at": s.starts_at.isoformat(), "format": s.format, "language": s.language,
                 "auditorium": s.auditorium.name},
        "movie": {"id": s.movie.id, "title": s.movie.title, "certificate": s.movie.certificate,
                  "runtime_minutes": s.movie.runtime_minutes},
        "theatre": {"id": theatre.id, "name": theatre.name, "city": theatre.city, "address": theatre.address,
                    "is_demo": theatre.is_demo},
    }
    if with_ticket and b.status.value == "CONFIRMED":
        data["ticket_payload"] = ticket_payload(b.reference)
    return data
