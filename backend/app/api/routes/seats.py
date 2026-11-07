import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.api.deps import DB, CurrentUser, Holds, OptionalUser, get_holds, user_from_token
from app.core.errors import AppError, bad_request, conflict, not_found
from app.core.security import hold_tag
from app.db.session import sessionmaker
from app.models import Seat, Show
from app.schemas.api import HoldIn, RecommendIn
from app.services.bookings import now_utc
from app.services.events import hub, publish_seats
from app.services.seatmap import build_seat_map, live_db_seats
from app.services.viewing import SeatInfo, recommend

router = APIRouter(tags=["seats"])


async def _show(db, show_id: str) -> Show:
    s = await db.get(Show, show_id)
    if not s or s.is_cancelled:
        raise not_found("Show")
    return s


@router.get("/shows/{show_id}/seats")
async def seat_map(show_id: str, db: DB, holds: Holds, user: OptionalUser):
    show = await _show(db, show_id)
    return await build_seat_map(db, holds, show, user.id if user else None)


@router.post("/shows/{show_id}/holds")
async def hold_seats(show_id: str, body: HoldIn, db: DB, holds: Holds, user: CurrentUser):
    show = await _show(db, show_id)
    if show.starts_at <= now_utc():
        raise bad_request("show_started", "This show has already started")
    ids = list(dict.fromkeys(body.seat_ids))
    seats = (await db.execute(select(Seat).where(Seat.id.in_(ids)))).scalars().all()
    if len(seats) != len(ids) or any(s.auditorium_id != show.auditorium_id for s in seats):
        raise bad_request("bad_seats", "Unknown seat for this show")
    if any(s.is_blocked for s in seats):
        raise conflict("seat_blocked", "That seat is not available")

    live = await live_db_seats(db, show_id)
    taken = [s.id for s in seats if s.id in live and live[s.id][1] != user.id]
    if taken:
        raise conflict("seat_taken", "Seat already taken", seat_ids=taken)

    res = await holds.hold(show_id, user.id, ids)
    if res.too_many:
        raise AppError(422, "too_many", "You can hold up to 10 seats at a time")
    if not res.ok:
        raise conflict("seat_taken", "Someone else is holding that seat", seat_ids=[res.conflict_seat])

    tag = hold_tag(user.id)
    await publish_seats(show_id, [{"seat_id": sid, "state": "held", "tag": tag} for sid in ids])
    return {"held": await holds.user_holds(show_id, user.id), "deadline_ms": res.deadline_ms}


@router.delete("/shows/{show_id}/holds")
async def release_seats(show_id: str, holds: Holds, user: CurrentUser, body: HoldIn | None = None):
    if body and body.seat_ids:
        freed = await holds.release(show_id, user.id, body.seat_ids)
    else:
        freed = await holds.release_all(show_id, user.id)
    await publish_seats(show_id, [{"seat_id": sid, "state": "available"} for sid in freed])
    return {"released": freed, "held": await holds.user_holds(show_id, user.id)}


@router.post("/shows/{show_id}/recommendations")
async def recommendations(show_id: str, body: RecommendIn, db: DB, holds: Holds, user: OptionalUser):
    show = await _show(db, show_id)
    data = await build_seat_map(db, holds, show, user.id if user else None)
    mine = data["my_tag"]
    pool = [
        SeatInfo(id=s["id"], row_label=s["row"], number=s["number"], block=s["block"], grid_row=s["grid_row"],
                 category=s["category"], price_paise=s["price_paise"], score=s["view"]["score"],
                 available=s["state"] == "available" or (s["state"] == "held" and mine and s["tag"] == mine))
        for s in data["seats"]
    ]
    return {"options": recommend(pool, body.group_size, body.max_price_per_seat, set(body.categories) or None)}


@router.websocket("/ws/shows/{show_id}")
async def seat_socket(ws: WebSocket, show_id: str):
    """Live seat updates. Client gets a full snapshot on connect, then deltas."""
    await ws.accept()
    token = ws.query_params.get("token")
    async with sessionmaker()() as db:
        show = await db.get(Show, show_id)
        if not show:
            await ws.close(code=4404)
            return
        user = await user_from_token(db, token)
        snapshot = await build_seat_map(db, get_holds(), show, user.id if user else None)
    await ws.send_text(json.dumps({"type": "snapshot", "seats": [
        {"seat_id": s["id"], "state": s["state"], "tag": s["tag"]} for s in snapshot["seats"]]}))
    await hub.join(show_id, ws)
    try:
        while True:
            # we only expect pings; anything else is ignored
            msg = await asyncio.wait_for(ws.receive_text(), timeout=60)
            if msg == "ping":
                await ws.send_text('{"type":"pong"}')
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        await hub.leave(show_id, ws)
