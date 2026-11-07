"""Spins up a real uvicorn process (with the sweeper on and a 2s hold window)
and checks that two clients see each other's seat changes live."""

import asyncio
import json
import os
import socket
import subprocess
import sys
import time

import httpx
import pytest
import websockets


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server():
    port = _free_port()
    env = {**os.environ, "CV_RUN_SWEEPER": "true", "CV_HOLD_SECONDS": "2", "CV_SWEEPER_INTERVAL_SECONDS": "0.3"}
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level",
                             "warning"], env=env, cwd=os.path.dirname(os.path.dirname(__file__)))
    base = f"http://127.0.0.1:{port}/api"
    for _ in range(50):
        try:
            if httpx.get(base + "/health").status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    yield base, f"ws://127.0.0.1:{port}/api"
    proc.terminate()
    proc.wait(5)


async def _next(ws, kind, timeout=5, where=lambda m: True):
    # other tests share this show, so skip unrelated broadcasts
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=end - time.monotonic()))
        if msg["type"] == kind and where(msg):
            return msg
    raise AssertionError(f"no {kind} message")


async def test_live_seat_updates_and_expiry_broadcast(live_server, show_id, seats):
    http, wsbase = live_server
    async with httpx.AsyncClient(base_url=http) as c:
        r = await c.post("/auth/register", json={"email": f"live{time.time_ns()}@example.com",
                                                 "password": "Passw0rd!", "full_name": "Live"})
        token = r.json()["access_token"]
        async with websockets.connect(f"{wsbase}/ws/shows/{show_id}") as watcher:
            snap = await _next(watcher, "snapshot")
            assert len(snap["seats"]) > 50
            sid = seats[0]["id"]
            await c.post(f"/shows/{show_id}/holds", json={"seat_ids": [sid]},
                         headers={"Authorization": f"Bearer {token}"})
            mine = lambda m: any(c["seat_id"] == sid for c in m["changes"])  # noqa: E731
            upd = await _next(watcher, "seats", where=mine)
            assert upd["changes"][0]["state"] == "held" and upd["changes"][0]["tag"]
            # 2s hold window on this server -> sweeper should announce the release
            freed = await _next(watcher, "seats", timeout=6, where=mine)
            assert freed["changes"] == [{"seat_id": sid, "state": "available"}]


async def test_presence_count(live_server, show_id):
    _, wsbase = live_server
    async with websockets.connect(f"{wsbase}/ws/shows/{show_id}") as a:
        await _next(a, "snapshot")
        async with websockets.connect(f"{wsbase}/ws/shows/{show_id}") as b:
            await _next(b, "snapshot")
            p = await _next(a, "presence")
            while p["viewers"] < 2:
                p = await _next(a, "presence")
            assert p["viewers"] == 2
