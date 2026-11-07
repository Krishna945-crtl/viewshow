import asyncio
import logging

from app.core.config import get_settings
from app.core.redis import get_redis
from app.db.session import sessionmaker
from app.services.bookings import expire_due
from app.services.events import publish_seats
from app.services.holds import HoldStore

log = logging.getLogger("cineverse.sweeper")


async def sweep_once() -> tuple[int, int]:
    holds = HoldStore(get_redis())
    freed = await holds.sweep()
    async with sessionmaker()() as db:
        # a hold that lapsed but is still covered by a pending booking stays 'held'
        from app.services.seatmap import live_db_seats
        n_seats = 0
        for show_id, seats in freed.items():
            live = await live_db_seats(db, show_id)
            really_free = [s for s in seats if s not in live]
            n_seats += len(really_free)
            await publish_seats(show_id, [{"seat_id": s, "state": "available"} for s in really_free])
        expired = await expire_due(db, holds)
    return n_seats, expired


async def run_forever():
    interval = get_settings().sweeper_interval_seconds
    while True:
        try:
            seats, bookings = await sweep_once()
            if seats or bookings:
                log.info("released %s held seats, expired %s bookings", seats, bookings)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("sweeper tick failed")
        await asyncio.sleep(interval)
