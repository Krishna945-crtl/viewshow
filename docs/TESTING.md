# Testing strategy

| Layer | Tool | Count | What it proves |
|---|---|---|---|
| Backend unit | pytest | 27 | layout geometry (aisles, arcs, risers, validation), theme engine (archetype detection for unseen movies, fallback, palette hints, clamping), view scoring, recommendations |
| Backend integration | pytest + httpx ASGI | 35 | auth (rotation, reuse detection, RBAC), holds, booking flow, payments, webhooks, expiry, late payments, cancellation, admin, validation errors |
| Concurrency | pytest + asyncio.gather | 4 | 30 users racing for one seat -> exactly 1 winner; overlapping group holds never split a seat; DB index blocks double booking even with Redis bypassed; 5 concurrent verifies -> one confirmation |
| Realtime | real uvicorn + websockets | 2 | snapshot, live hold broadcast, sweeper-driven expiry broadcast, presence |
| Frontend unit | vitest | 8 | theme crossfade maths, particle swap, reduced-motion instant mode, arc-focus recovery, seat-state logic |
| End-to-end | Playwright (desktop + Pixel 7) | 5 x 2 | full booking with sandbox payment and ticket, declined card retry, keyboard 2D map, 3D viewpoints, two browsers seeing each other's holds live |

## Running

Backend (needs Postgres + Redis; uses database `cineverse_test` and Redis db 15):

```bash
cd backend && python -m pytest -q
```

Frontend unit:

```bash
cd frontend && npx vitest run
```

End-to-end (API with relaxed sign-up limit + static build):

```bash
cd backend && CV_REGISTER_LIMIT_PER_HOUR=1000 uvicorn app.main:app --port 8000
```

```bash
cd frontend && npx next build && python3 -m http.server 3000 -d out
```

```bash
cd frontend && npx playwright test --trace off
```

Set `PW_CHROMIUM=/path/to/chrome` to reuse an installed browser. Headless runs use SwiftShader for WebGL.

## Not automated (do these by hand before a release)

* Real-device 3D on a mid-range Android phone and an iPhone (touch orbit, pinch, seat taps, frame rate).
* Razorpay test-mode checkout with real test keys + a webhook pointed at a public URL (ngrok or staging).
* Screen reader pass (TalkBack / VoiceOver) on the 2D map and checkout.
