# Reservation & payment flows

## Selecting seats (hold)

```mermaid
sequenceDiagram
  participant U as User A
  participant API
  participant R as Redis
  participant PG as Postgres
  participant V as Other viewers
  U->>API: POST /shows/S/holds {F12}
  API->>PG: seat belongs to show? not blocked? no live booking row?
  API->>R: HOLD_LUA (atomic) - every seat free or already mine? count <= 10?
  alt someone else holds a seat
    R-->>API: {-1, seat}
    API-->>U: 409 seat_taken
  else ok
    R-->>API: {1, deadline}  (deadline fixed at first hold, adding seats never extends it)
    API->>R: PUBLISH cv:show:S {F12 held, tag}
    R-->>V: (every API process relays to its websockets)
    API-->>U: {held, deadline_ms}
  end
```

## Booking + payment

```mermaid
sequenceDiagram
  participant U as User
  participant API
  participant R as Redis
  participant PG as Postgres
  participant P as Razorpay / sandbox
  U->>API: POST /bookings {seats}
  API->>R: are all seats held by me?
  API->>PG: INSERT booking PENDING + booking_seats(active)  -- partial unique index
  PG-->>API: ok (or IntegrityError -> 409)
  U->>API: POST /payments/order
  API->>P: create order (amount from DB, never from client)
  U->>P: checkout
  P-->>U: order_id, payment_id, signature
  U->>API: POST /payments/verify
  API->>API: HMAC(order|payment) == signature ?
  API->>PG: SELECT booking FOR UPDATE
  alt already CONFIRMED
    API-->>U: same booking (idempotent)
  else PENDING
    API->>PG: CONFIRMED, payment CAPTURED
    API->>R: release holds, PUBLISH booked
    API-->>U: ticket (QR = CV3D|REF|HMAC)
  end
  P-->>API: webhook payment.captured (maybe before/after verify)
  API->>PG: INSERT webhook_events(id) - duplicate? stop
  API->>API: same confirm path (idempotent)
```

## Failure & expiry paths

```mermaid
stateDiagram-v2
  [*] --> PENDING_PAYMENT: create booking
  PENDING_PAYMENT --> CONFIRMED: verified payment / webhook
  PENDING_PAYMENT --> PENDING_PAYMENT: card declined (retry allowed)
  PENDING_PAYMENT --> EXPIRED: sweeper, after payment window
  PENDING_PAYMENT --> CANCELLED: user / new booking replaces it
  EXPIRED --> CONFIRMED: late payment AND seats still free
  EXPIRED --> EXPIRED: late payment, seats resold -> payment REFUND_PENDING
  CONFIRMED --> CANCELLED: user (>2h before) / admin / show cancelled -> REFUND_PENDING
```

* **Abandoned selection** - Redis key TTL ends the hold; the sweeper sees it in the expiry zset and broadcasts
  `available` (unless a pending booking still covers the seat).
* **Abandoned checkout** - `expires_at` passes; sweeper flips to `EXPIRED`, deactivates `booking_seats`, broadcasts.
* **Two people, one seat** - Redis Lua is atomic, so exactly one hold wins. If a bug ever skipped Redis, the
  partial unique index still lets only one booking row become live (both are covered by tests).
* **Double click / retries** - order creation reuses the open order; verify and webhooks are idempotent.
