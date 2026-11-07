# CineVerse 3D

Movie ticket booking app with an interactive 3D auditorium. Works on web, Android and iOS.

## Workflow

```
Select Movie → Select City & Theatre → Select Date & Showtime → Enter 3D Auditorium
→ Explore & Select Seats → View From My Seat → Confirm Seats → Pay → Digital Ticket (QR)
```

1. **Home** – browse movies by city, genre and language. Each movie has its own auditorium theme.
2. **Movie details** – synopsis, cast, trailer and a preview of the auditorium atmosphere.
3. **Showtimes** – pick a date, theatre and show time.
4. **Seat selection** – choose seats in the 3D auditorium or the 2D seat map.
   - Seat states: Available, Selected, Held, Booked, Blocked.
   - Selected seats are held for 5 minutes.
   - Other users' selections appear live.
   - **View From My Seat** moves the camera to eye level at that seat and shows distance, viewing angle and screen size.
   - **Best seats** suggests seats for a group size and budget.
5. **Checkout** – booking summary and payment (sandbox mode).
6. **Ticket** – digital ticket with QR code.
7. **Profile** – upcoming and past bookings, cancellation.
8. **Admin** – manage movies, themes, theatres, seat layouts, shows, bookings, ticket check-in and stats.

> Theatres in the seed data are demo venues with simulated seats. Payments run in sandbox mode.

## Themes for any movie

The auditorium re-lights itself for **every** film — not just the three reference looks (Dune, Godzilla,
Avengers). Nothing is hard-coded per title.

- Reads genres, title, synopsis, TMDB keywords, mood tags, colour words and the poster's colours.
- Scores 27 visual looks (ocean, desert, sky, underworld, mythic, pop, noir, stage …), blends the top two.
- Paints with the movie's own poster colours when available, then gives each film a small signature shift
  so no two movies look the same.
- Every theme comes with **"Why this look?"** — the exact signals that chose it.
- Seat status colours never change, so availability is always readable.

Examples from the seed data: Pushpa 2 → gritty gold & smoke, Barbie → candy pop pink, Avatar: The Way of Water →
abyssal blue, Kalki 2898 AD → saffron & temple gold, La La Land → spotlight & velvet. Try your own film in
**Theme Lab** (`/lab`). Details: `docs/THEME_ENGINE.md`.

### Add any real movie

- **Admin → Movies → Import from TMDB**: search, click Import — genres, keywords, cast, trailer, certificate
  and poster colours come in and the theme is ready. Needs a free key from
  https://www.themoviedb.org/settings/api in `backend/.env` as `CV_TMDB_API_KEY`.
- **By hand**: title + genres + one line of synopsis is enough. Upload the poster to use its colours (the image
  is only kept if you confirm you have the rights to show it).

## Tech stack

| Part | Stack |
|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind CSS, React Three Fiber, Three.js, Drei, Framer Motion |
| Mobile | Capacitor (Android / iOS) |
| Backend | Python, FastAPI, WebSockets |
| Database | PostgreSQL, Redis |
| Payments | Razorpay (test mode) / local sandbox |
| Deployment | Docker, Docker Compose |

## Steps to run

### Option 1 – Docker

```bash
docker compose up --build
```

- Web: http://localhost:3000
- API docs: http://localhost:8000/api/docs

### Option 2 – Manual setup

Requirements: Python 3.12+, Node 22, PostgreSQL 16, Redis 7.

**Backend**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

### Demo logins

| Role | Email | Password |
|---|---|---|
| User | demo@cineverse.dev | Demo@1234 |
| Admin | admin@cineverse.dev | Admin@123 |

## Steps to test

```bash
cd backend && python -m pytest -q
```

```bash
cd frontend && npx vitest run
```

```bash
cd frontend && npx playwright test --trace off
```

End-to-end tests need the API running on port 8000 and the built site on port 3000 – see `docs/TESTING.md`.

## Steps to build Android / iOS

```bash
cd frontend
npx next build
npx cap add android
npx cap add ios
npx cap sync
npx cap open android
npx cap open ios
```

Set `NEXT_PUBLIC_API_URL` to a reachable API address before building for a phone.

## Documentation

- `docs/ARCHITECTURE.md` – system design, folder structure, database schema
- `docs/API.md` – API endpoints
- `docs/FLOWS.md` – reservation and payment flows
- `docs/TESTING.md` – testing strategy
- `docs/DEPLOYMENT.md` – deployment steps
- `docs/IMPLEMENTATION_GUIDE.md` – phase-wise implementation guide
- `docs/THEME_ENGINE.md` – how any movie gets its theme, with worked examples
