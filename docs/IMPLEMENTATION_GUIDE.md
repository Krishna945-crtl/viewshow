# Implementation guide

How the project was built, in the order you'd rebuild or extend it. Every phase ended with its tests green.

## Phase 1 - Foundation
1. Postgres + Redis, FastAPI skeleton, settings (`app/core/config.py`), async SQLAlchemy.
2. Models + Alembic migration `0001` (users, catalog, venues, seats, shows, bookings, payments).
3. Auth: argon2 hashing, short JWT access + rotating refresh tokens, admin role.
4. Layout builder (`services/layout.py`) -> seats with coordinates; seed script.
5. Catalog endpoints; Next.js static-export app: home, movie, showtimes, accessible 2D seat map.

## Phase 2 - 3D auditorium
1. `Auditorium3D` canvas, `Room` (arc risers, walls, light strips), curved `Screen`.
2. `Seats`: 4 instanced category meshes + instanced number-plate shader; raycast picking; hover tooltip.
3. `CameraRig`: overview / back / side / stage viewpoints, reset, seat view at eye height.
4. `viewing.py` metrics served with every seat -> `SeatViewPanel`.

## Phase 3 - Theme engine
1. `theme_engine.py`: archetypes, scoring, blending, palette hints, title fallback, `guard()`.
2. Admin themes CRUD + preview. Client `ThemeState` easing; lights/fog/particles/screen read from it.
3. Theme Lab page; CSS `@property` colour transitions; procedural ambience.

## Phase 4 - Booking reliability
1. Redis Lua holds with fixed deadlines + expiry zset; sweeper.
2. Booking creation guarded by holds and the partial unique index.
3. Payment providers (sandbox + Razorpay), verify, webhook dedupe, late-payment handling, cancellations.
4. WebSocket hub over Redis pub/sub; client store shared by 2D and 3D.
5. Concurrency tests.

## Phase 5 - Mobile
1. Mobile-first layouts, safe areas, 44 px touch targets, bottom nav.
2. GPU tiering, adaptive DPR, slow-device -> 2D suggestion, lazy 3D bundle.
3. Capacitor config; `cap add android` verified. Device testing is the remaining manual step.

## Phase 6 - Testing & deployment
Playwright desktop + mobile, vitest, CI workflow, Dockerfiles + compose, docs.

## Extending

* **New archetype** - add an entry to `ARCHETYPES` (genres, words, colours, particles, sound) + a test case.
* **New particle kind** - add a branch in `Particles.tsx` vertex shader and to `PARTICLES` in the engine.
* **New seat category** - extend `SeatCategory`, `SEAT_SPECS`, `seatGeometry()` and `SEAT_WIDTH`.
* **Real inventory** - implement an adapter that maps a partner's seat map to the layout format and
  replaces holds/booking calls with the partner API. Only with an authorised partnership.

## Ideas for next versions
* AR/VR seat preview (WebXR) - kept out of v1 on purpose.
* Poster colour extraction on upload to fill `palette_hint` automatically.
* Seat-map heatmap of popularity for admins; dynamic pricing experiments.
* Push notifications for show reminders (Capacitor Push).
