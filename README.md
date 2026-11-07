# CineVerse 3D

Movie ticket booking app with an interactive 3D auditorium. Works on web, Android and iOS.

## Workflow

```
Select Movie → Select City & Theatre → Select Date & Showtime → Enter 3D Auditorium
→ Explore & Select Seats → View From My Seat → Confirm Seats → Pay → Digital Ticket (QR)
```

1. **Home** – browse movies by city, genre and language. Each movie has its own colour theme.
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
