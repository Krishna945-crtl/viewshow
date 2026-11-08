# Architecture

```mermaid
flowchart LR
  subgraph Clients
    W[Browser<br/>desktop / mobile]
    A[Android app<br/>Capacitor]
    I[iOS app<br/>Capacitor]
  end
  W & A & I --> FE[Next.js static export<br/>React · R3F · Tailwind]
  FE -- REST /api --> API[FastAPI]
  FE <-- WebSocket /api/ws/shows/:id --> API
  API --> PG[(PostgreSQL<br/>users · catalog · bookings · payments)]
  API --> RD[(Redis<br/>seat holds · pub/sub · rate limits)]
  API -- orders / verify --> RZ[Razorpay test mode<br/>or local sandbox]
  RZ -- webhook --> API
  SW[Sweeper task<br/>in every API process] --> RD & PG
```

* The frontend is a **static export** - no Node server in production. The same `out/` folder is served by
  nginx and bundled into the Android/iOS shells. Dynamic ids travel in query strings (`/seats/?show=…`)
  so every route can be pre-rendered.
* The backend is **stateless**. Seat holds live in Redis, confirmed seats in Postgres, and seat changes are
  published to Redis so any number of API processes can serve WebSocket clients.
* A small sweeper loop (every 2 s) announces expired holds and expires unpaid bookings. It uses
  `FOR UPDATE SKIP LOCKED`, so running it in several processes is safe.

## Folder structure

```
backend/
  app/
    main.py                 app factory, middleware (request id, error log), lifespan (hub + sweeper)
    seed.py                 demo data: themes, 22 movies (13 fictional + 9 real titles), 6 venues, 3 layouts, a week of shows
    core/                   config, security (argon2, JWT, HMAC), redis, rate limit, errors
    db/                     async engine/session, declarative base with naming conventions
    models/entities.py      SQLAlchemy models
    schemas/api.py          Pydantic request models + validation
    api/deps.py             DB / auth / admin / hold-store dependencies
    api/serializers.py      response shaping
    api/routes/             auth, catalog, seats (+ websocket), bookings, payments, admin
    services/
      layout.py             authored layout -> seat coordinates (arcs, aisles, risers)
      viewing.py            view metrics + group recommendations
      theme_engine.py       dynamic movie theme engine (scoring, blending, guard, explain)
      theme_lexicon.py      27 visual archetypes, every TMDB genre, colour words
      palette.py            poster -> dominant colours (Pillow, bomb-safe)
      storage.py            object storage for authorised artwork (local disk, S3-swappable)
      tmdb.py               optional "import any real movie" client
      holds.py              Redis Lua seat holds
      bookings.py           booking lifecycle (create / confirm / release / expire)
      payments.py           mock + Razorpay providers
      seatmap.py            seat state snapshot
      events.py             Redis pub/sub -> websocket hub
      sweeper.py            hold + booking expiry loop
  alembic/                  migrations
  tests/                    pytest suites

frontend/
  src/app/                  routes: / (splash) login register home movie showtimes seats checkout ticket profile lab admin
  src/components/
    theatre/                the 3D auditorium (see below)
    seats/                  2D map, legend, hold timer, seat view panel, recommendations
    admin/                  dashboard tabs
    ui/                     shell, poster art, toasts, theme applier, sound control
  src/lib/                  api client, auth/prefs/seat stores, theme helpers, ambience synth, webgl detection
  e2e/                      Playwright specs
  capacitor.config.ts
```

## Database

```mermaid
erDiagram
  users ||--o{ refresh_tokens : has
  users ||--o{ bookings : makes
  movie_themes |o--o{ movies : styles
  movies ||--o{ shows : screened_in
  theatres ||--o{ auditoriums : contains
  auditoriums ||--o{ seats : has
  auditoriums ||--o{ shows : hosts
  shows ||--o{ show_prices : priced_by
  shows ||--o{ bookings : for
  bookings ||--o{ booking_seats : holds
  seats ||--o{ booking_seats : in
  bookings ||--o{ payments : paid_by
```

Key constraints:

| Table | Constraint | Why |
|---|---|---|
| `booking_seats` | `UNIQUE (show_id, seat_id) WHERE active` | No two live bookings can ever own a seat - enforced by Postgres even if app code or Redis misbehaves |
| `payments` | `UNIQUE provider_order_id`, `UNIQUE provider_payment_id` | One order per attempt; a payment id can't confirm two bookings |
| `webhook_events` | PK = provider event id | Replayed webhooks become no-ops |
| `seats` | `UNIQUE (auditorium_id, label)` | Seat labels are stable identifiers |
| `auditoriums` | `UNIQUE (theatre_id, name)` | |

Money is stored in paise (integers). Seats carry real-world coordinates in metres (`x` across, `y` floor height,
`z` distance from the screen plane, `yaw` rotation) computed once from the layout.

## Auditorium layout format

```json
{
  "screen": {"width": 15, "height": 6.4, "curvature": 0.22, "distance": 7, "bottom": 1.5},
  "aisle_width": 1.3, "arc_focus": 24, "rise_per_row": 0.34, "flat_rows": 2,
  "rows": [
    {"label": "A", "category": "standard", "blocks": [5, 12, 5]},
    {"label": "L", "category": "recliner", "blocks": [3, 8, 3], "accessible": [1, 14], "blocked": [], "gap_before": 0.4}
  ]
}
```

`blocks` are seat counts per section; gaps between blocks become aisles (and empty columns in the 2D grid).
`arc_focus > 0` bends rows into arcs around a point behind the screen, rotating seats to face the centre.
Seat width and row pitch depend on category. `layout.py` validates and expands this into seats.

## Dynamic Movie Theme Engine

Works for **any** movie - nothing is hard-coded per title. Full write-up with worked examples: `THEME_ENGINE.md`.

```mermaid
flowchart TD
  M[movie metadata<br/>genres · title · tagline · synopsis · TMDB keywords · mood tags] --> C{curated theme attached?}
  C -- yes --> G[guard: validate + clamp]
  C -- no --> S[score 27 archetypes<br/>genre prior · title ×2.5 · story ×1.2 · keyword ×2 · mood tag ×3 · colour evidence]
  ART[poster upload / TMDB poster] --> PAL[palette.py: dominant colours]
  PAL --> S
  S --> B{any match?}
  B -- yes --> X[top archetype, blend 2nd in proportion to its score]
  B -- no --> H[title hash -> signature palette]
  X --> P[paint with poster colours, then admin hex picks]
  H --> P
  P --> SIG[per-title signature: small hue drift + fog/pulse wobble]
  SIG --> E[expand to full config:<br/>palette · lighting · fog · screen · particles · animation · sound]
  E --> G
  G --> OUT[theme JSON + explain block sent with every movie]
```

Archetypes: desert, wasteland, ocean, sky, cosmic, tech, neon, horror, inferno, frost, jungle, noir, underworld,
kinetic, suspense, romance, pop, whimsy, sunny, stage, royal, mythic, battlefield, period, intimate, arena.
Every TMDB genre (and labels like Mythological, Masala, Superhero, Sci-Fi) maps to at least one. Adding a look
is one entry in `theme_lexicon.py`.

Every auto theme carries `explain`: confidence, the top three archetypes with the exact evidence that scored
them ("genre Crime", "story 'sandalwood'", "poster #ff3fa4"), and where the colours came from. The admin editor,
Theme Lab and movie page show it as "Why this look?".

`guard()` is the safety net for both auto and admin themes: backgrounds stay dark, light colours stay bright
enough to light anything, ambient intensity/fog/particle density are capped (back rows stay visible, phones
stay cool), unknown particle or sound presets fall back. It is idempotent and an `explain` block is only ever
kept on server-generated themes. **Seat status colours are not part of a theme** - they are fixed and drawn
unlit, so availability reads the same under every film.

Poster images are optional and never required: only their colours are stored unless an admin confirms the
image is licensed to display. TMDB posters are shown only when `CV_TMDB_SHOW_POSTERS` is on (allowed by the
TMDB API terms, with the attribution line the app prints on those movies).

On the client, `ThemeState` keeps the *displayed* values and eases toward the target every frame
(`1 - e^(-k·dt)`, with k from `transition_ms`). Lights, fog, screen shader, wall strips, seat fabric and
particles all read from it, so a theme switch is a crossfade with no React re-render and no scene rebuild.
Particles fade out, swap type, and fade back in. CSS custom properties are registered with `@property`
so the 2D UI shifts colour smoothly too.

## 3D auditorium implementation

| Piece | How | Cost |
|---|---|---|
| Seats | one `InstancedMesh` per category (4 low-poly merged models) | 4 draw calls for any hall size |
| Number plates | one `InstancedMesh` + custom shader: status colour + seat number from a canvas atlas, unlit, fog-free | 1 draw call |
| Risers | per-row extruded arc slabs merged into one geometry, glowing nosing merged into another | 2 draw calls |
| Walls, panels, light strips | boxes + instanced panels; emissive materials driven by theme | ~12 |
| Screen | curved plane, shader with slow original gradient loop | 1 |
| Particles | one `Points`, all motion in the vertex shader, 12 kinds | 1 |
| Lighting | ambient + hemisphere + key + 2 rim + screen spot; **no realtime shadows** | |

* Picking uses R3F raycasting on instanced meshes (`instanceId` -> seat); drags > 8 px aren't clicks.
* Cameras: drei `CameraControls` with smooth transitions. Viewpoints: overview, back row, side, from stage,
  and seat view (eye height 1.15 m above the row floor, look-around limited to ±70°, zoom/pan disabled,
  plates hidden so they don't block the screen).
* Performance: `detectGpu()` picks low/high quality (DPR, antialias, particle count); drei
  `PerformanceMonitor` lowers DPR when FPS drops and, if it keeps dropping, offers the 2D map. No WebGL ->
  2D only. The 3D bundle is lazy-loaded (`next/dynamic`, `ssr:false`), so the 2D path never downloads three.js.
* Reduced motion: instant theme switches, no particles, no light pulse, camera jumps instead of flying.

## Booking states

| UI state | Source |
|---|---|
| Available | not blocked, no live booking row, no Redis hold |
| Selected | Redis hold whose tag = my tag |
| Held | someone else's Redis hold, or a `PENDING_PAYMENT` booking |
| Booked | `CONFIRMED` booking |
| Blocked | `seats.is_blocked` |

The hold "tag" is an HMAC of the user id, so clients can tell "mine" from "theirs" without learning user ids.

## UI component map

* `AppShell` - header/bottom nav, auth + prefs hydration, skip link, toasts
* `ThemeApplier` - pushes a movie's palette into CSS variables
* `PosterArt` - generated SVG key art from theme + title hash (no copyrighted posters)
* `SeatMap2D` - accessible grid, roving tabindex, arrow-key navigation, symbols + patterns per state
* `Auditorium3D` -> `Lights`, `Room`, `Screen`, `Seats`, `Particles`, `CameraRig`
* `SeatViewPanel` - score ring, view metrics, estimate label, prev/next seat, select/remove
* `Recommendations` - group size + budget -> ranked options with preview / pick
* `HoldTimer`, `Legend`, `SoundControl`
* Admin: `Overview`, `Movies`, `Themes` (live 3D preview), `Venues` (layout JSON + top-down preview),
  `Shows`, `Bookings` (+ QR check-in), `Errors`
