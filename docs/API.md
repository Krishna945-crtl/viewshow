# API reference

Base URL `/api`. Interactive docs: `/api/docs` (OpenAPI). JSON in and out; money in **paise**.
Auth: `Authorization: Bearer <access_token>`. Errors always look like:

```json
{"detail": {"code": "seat_taken", "message": "Someone else is holding that seat", "seat_ids": ["..."]}}
```

## Auth

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/register` | `{email, password, full_name, city?}` -> tokens + user. Rate limited per IP |
| POST | `/auth/login` | `{email, password}` -> tokens + user. Rate limited |
| POST | `/auth/refresh` | `{refresh_token}` -> new pair. Rotation; reusing an old token revokes the whole family |
| POST | `/auth/logout` | `{refresh_token}` |
| GET / PATCH | `/auth/me` | profile |

Access tokens: JWT HS256, 30 min. Refresh tokens: random, stored as SHA-256, 14 days.

## Catalog (public)

| Method | Path | Notes |
|---|---|---|
| GET | `/movies?q=&genre=&city=&language=` | active movies, each with its resolved `theme` |
| GET | `/movies/{id or slug}` | full detail |
| GET | `/movies/{id}/showtimes?city=&date=YYYY-MM-DD` | `{movie, dates[], theatres:[{theatre, shows[]}]}` (dates in IST) |
| GET | `/shows/{id}` | show + movie + theatre |
| GET | `/genres`, `/cities`, `/theatres?city=` | |
| POST | `/themes/preview` | `{title, genres[], keywords[], mood_tags[], synopsis, palette_hint[], art_palette[]}` -> generated theme with `explain` |
| POST | `/themes/preview-art` | multipart `file` (JPEG/PNG/WebP, ≤ 6 MB) -> `{art_palette:[{hex, weight}]}`. Nothing stored; rate-limited |

## Seats

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/shows/{id}/seats` | optional | full seat map: layout meta, prices, `my_tag`, `hold_deadline_ms`, seats with position, state, tag, view metrics |
| POST | `/shows/{id}/holds` | user | `{seat_ids}` -> `{held, deadline_ms}`. All-or-nothing. 409 `seat_taken`, 422 `too_many` |
| DELETE | `/shows/{id}/holds` | user | `{seat_ids}` or empty body = release all mine |
| POST | `/shows/{id}/recommendations` | optional | `{group_size, max_price_per_seat?, categories[]}` -> ranked options |

### WebSocket `/api/ws/shows/{id}?token=<access>`

Server -> client:

```json
{"type": "snapshot", "seats": [{"seat_id": "...", "state": "available|held|booked|blocked", "tag": "a1b2..."}]}
{"type": "seats", "show_id": "...", "changes": [{"seat_id": "...", "state": "held", "tag": "a1b2..."}]}
{"type": "presence", "viewers": 3}
```

Client sends `ping` at least every 60 s (the app sends every 25 s); server answers `{"type":"pong"}`.
A held seat whose `tag` equals your `my_tag` is your own selection.

## Bookings

| Method | Path | Notes |
|---|---|---|
| POST | `/bookings` | `{show_id, seat_ids}` - requires a live hold on every seat. 201 `PENDING_PAYMENT`. Replaces your older pending booking for that show |
| GET | `/bookings` | my bookings |
| GET | `/bookings/{id}` | includes `ticket_payload` once confirmed |
| POST | `/bookings/{id}/cancel` | pending any time; confirmed up to 2 h before the show (refund flagged) |

## Payments

| Method | Path | Notes |
|---|---|---|
| GET | `/payments/config` | `{provider, key_id, sandbox}` |
| POST | `/payments/order` | `{booking_id}` -> `{order_id, amount_paise, provider, key_id}`. Reuses an open order (double-click safe) |
| POST | `/payments/verify` | `{booking_id, razorpay_order_id, razorpay_payment_id, razorpay_signature}` -> confirmed booking. Idempotent |
| POST | `/payments/failed` | `{booking_id}` marks the attempt failed; booking stays payable until it expires |
| POST | `/payments/mock/checkout` | sandbox simulator only: `{order_id, outcome: success|failure}` |
| POST | `/payments/webhook/razorpay` | verifies `X-Razorpay-Signature`; dedupes on event id; handles `payment.captured`, `order.paid`, `payment.failed` |

## Admin (requires `is_admin`)

| Method | Path |
|---|---|
| GET/POST | `/admin/movies`, PUT/DELETE `/admin/movies/{id}` (delete = archive) |
| POST | `/admin/movies/{id}/artwork` multipart `file`, `keep_image` - poster colours -> theme; image kept only if `keep_image=true` |
| DELETE | `/admin/movies/{id}/artwork` - forget the colours (and our stored poster) |
| GET | `/admin/tmdb/status` - is TMDB import configured |
| GET | `/admin/tmdb/search?q=&year=` - TMDB hits, each with `imported_id` if already in the catalogue |
| POST | `/admin/tmdb/import/{tmdb_id}` - creates the movie (genres, keywords, cast, trailer, certificate, poster colours); 409 if already imported |
| GET/POST | `/admin/themes`, PUT/DELETE `/admin/themes/{id}`, POST `/admin/themes/preview` |
| POST | `/admin/theatres`, PUT `/admin/theatres/{id}` |
| POST | `/admin/layouts/validate` - returns summary + seat preview without saving |
| POST | `/admin/theatres/{id}/auditoriums`, GET/PUT `/admin/auditoriums/{id}` (layout edits refused once seats were booked) |
| GET/POST | `/admin/shows` (overlap-checked), POST `/admin/shows/{id}/cancel` |
| GET | `/admin/bookings?status=&q=`, POST `/admin/bookings/{id}/cancel` |
| POST | `/admin/tickets/check-in` `{payload}` - verifies the QR signature, records first scan |
| GET | `/admin/stats`, `/admin/errors` |
