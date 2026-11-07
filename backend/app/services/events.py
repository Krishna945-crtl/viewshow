"""Seat-change fan-out.

Every API instance publishes to Redis; every instance relays to its own
websocket clients. That way it scales past one process without sticky sessions.
"""

import asyncio
import json
import logging
from collections import defaultdict

from fastapi import WebSocket

from app.core.redis import get_redis

log = logging.getLogger("cineverse.events")
CHANNEL = "cv:show:"


async def publish_seats(show_id: str, changes: list[dict]):
    if not changes:
        return
    msg = json.dumps({"type": "seats", "show_id": show_id, "changes": changes})
    await get_redis().publish(CHANNEL + show_id, msg)


class WsHub:
    def __init__(self):
        self.rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._task: asyncio.Task | None = None

    def start(self):
        if self._task is None:
            self._task = asyncio.create_task(self._listen())

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None

    async def join(self, show_id: str, ws: WebSocket):
        self.rooms[show_id].add(ws)
        await self.broadcast_presence(show_id)

    async def leave(self, show_id: str, ws: WebSocket):
        self.rooms[show_id].discard(ws)
        if not self.rooms[show_id]:
            self.rooms.pop(show_id, None)
        else:
            await self.broadcast_presence(show_id)

    async def broadcast_presence(self, show_id: str):
        await self._send_local(show_id, json.dumps({"type": "presence", "viewers": len(self.rooms.get(show_id, ()))}))

    async def _send_local(self, show_id: str, text: str):
        dead = []
        for ws in list(self.rooms.get(show_id, ())):
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.rooms[show_id].discard(ws)

    async def _listen(self):
        while True:
            try:
                pubsub = get_redis().pubsub()
                await pubsub.psubscribe(CHANNEL + "*")
                async for msg in pubsub.listen():
                    if msg.get("type") != "pmessage":
                        continue
                    show_id = msg["channel"][len(CHANNEL):]
                    if show_id in self.rooms:
                        await self._send_local(show_id, msg["data"])
            except asyncio.CancelledError:
                raise
            except Exception:  # redis blip -> back off and resubscribe
                log.exception("pubsub listener crashed, retrying")
                await asyncio.sleep(1)


hub = WsHub()
