# Deployment

## Docker Compose (single host)

```bash
cp backend/.env.example .env    # set CV_JWT_SECRET, CV_TICKET_SIGNING_SECRET, payment keys
docker compose up --build -d
```

The API container runs `alembic upgrade head`, seeds only if the DB is empty, then serves with 2 workers.
The web container is nginx serving the static export. Set the build arg `NEXT_PUBLIC_API_URL` to the public
API URL.

## Production checklist

* Strong random `CV_JWT_SECRET` and `CV_TICKET_SIGNING_SECRET` (32+ bytes each).
* `CV_CORS_ORIGINS` = your web origin + `capacitor://localhost` + `http://localhost` (Android WebView).
* TLS in front of both services (the WebSocket becomes `wss://` automatically).
* Managed Postgres with backups; Redis with persistence off is fine (holds are meant to be short-lived).
* Scale API horizontally - holds and pub/sub are in Redis, the sweeper is multi-process safe.
* Ship logs; `/admin/errors` shows unhandled exceptions with request ids (`x-request-id` header).

## Razorpay test mode

1. Create test keys in the Razorpay dashboard (they start with `rzp_test_`).
2. Set `CV_PAYMENT_PROVIDER=razorpay`, `CV_RAZORPAY_KEY_ID`, `CV_RAZORPAY_KEY_SECRET`.
3. Add a webhook to `https://<api>/api/payments/webhook/razorpay` for `payment.captured`, `payment.failed`,
   `order.paid` and put its secret in `CV_RAZORPAY_WEBHOOK_SECRET`.
4. The frontend loads Razorpay Checkout automatically when `/payments/order` reports `provider: razorpay`.

Keep test keys until a real cinema partnership and authorised inventory integration exist.

## Android & iOS (Capacitor)

The static export is the app. Point it at a reachable API first - a phone can't reach `localhost`.

```bash
cd frontend
echo "NEXT_PUBLIC_API_URL=https://api.your-domain.com/api" > .env.production
npx next build
npx cap add android      # once (needs Android Studio + SDK to build)
npx cap add ios          # once (needs macOS + Xcode)
npx cap sync
npx cap open android     # build / run from Android Studio
npx cap open ios         # build / run from Xcode
```

Device testing notes:

* Test 3D on a real mid-range Android device - emulators use software GL and will trigger the 2D suggestion.
* iOS WebKit: confirm pinch-zoom inside the canvas doesn't zoom the page (`touch-action: none` is set on the canvas wrapper).
* Ambience needs a user tap to start audio on iOS - the sound toggle provides it.
