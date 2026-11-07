import asyncio

from app.core.redis import get_redis
from app.services.holds import HoldStore


async def test_hold_and_release_via_api(client, register, show_id, seats):
    h, _ = await register()
    sid = seats[0]["id"]
    r = await client.post(f"/shows/{show_id}/holds", json={"seat_ids": [sid]}, headers=h)
    assert r.status_code == 200 and r.json()["held"] == [sid]

    m = (await client.get(f"/shows/{show_id}/seats", headers=h)).json()
    mine = next(s for s in m["seats"] if s["id"] == sid)
    assert mine["state"] == "held" and mine["tag"] == m["my_tag"]
    assert m["hold_deadline_ms"]

    r = await client.request("DELETE", f"/shows/{show_id}/holds", json={"seat_ids": [sid]}, headers=h)
    assert r.json()["released"] == [sid]


async def test_someone_elses_hold_blocks_me(client, register, show_id, seats):
    a, _ = await register("a")
    b, _ = await register("b")
    sid = seats[1]["id"]
    assert (await client.post(f"/shows/{show_id}/holds", json={"seat_ids": [sid]}, headers=a)).status_code == 200
    r = await client.post(f"/shows/{show_id}/holds", json={"seat_ids": [sid]}, headers=b)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "seat_taken"
    # b cannot release a's seat either
    r = await client.request("DELETE", f"/shows/{show_id}/holds", json={"seat_ids": [sid]}, headers=b)
    assert r.json()["released"] == []


async def test_max_seats(client, register, show_id, seats):
    h, _ = await register()
    ids = [s["id"] for s in seats[:10]]
    assert (await client.post(f"/shows/{show_id}/holds", json={"seat_ids": ids}, headers=h)).status_code == 200
    r = await client.post(f"/shows/{show_id}/holds", json={"seat_ids": [seats[10]["id"]]}, headers=h)
    assert r.status_code == 422


async def test_all_or_nothing(client, register, show_id, seats):
    a, _ = await register()
    b, _ = await register()
    await client.post(f"/shows/{show_id}/holds", json={"seat_ids": [seats[2]["id"]]}, headers=a)
    r = await client.post(f"/shows/{show_id}/holds", json={"seat_ids": [seats[3]["id"], seats[2]["id"]]}, headers=b)
    assert r.status_code == 409
    owners = await HoldStore(get_redis()).owners(show_id)
    assert seats[3]["id"] not in owners  # nothing partially held


async def test_adding_seats_does_not_extend_deadline(show_id):
    store = HoldStore(get_redis())
    r1 = await store.hold(show_id, "u1", ["s1"], ttl_s=60)
    await asyncio.sleep(0.05)
    r2 = await store.hold(show_id, "u1", ["s2"], ttl_s=60)
    assert r1.deadline_ms == r2.deadline_ms


async def test_expired_holds_are_swept(show_id):
    store = HoldStore(get_redis())
    await store.hold(show_id, "u1", ["sx", "sy"], ttl_s=0.3)
    assert set((await store.owners(show_id)).keys()) == {"sx", "sy"}
    await asyncio.sleep(0.45)
    freed = await store.sweep()
    assert sorted(freed[show_id]) == ["sx", "sy"]
    assert await store.owners(show_id) == {}
    # and the seat is free for someone else now
    assert (await store.hold(show_id, "u2", ["sx"])).ok


async def test_holds_need_login(client, show_id, seats):
    r = await client.post(f"/shows/{show_id}/holds", json={"seat_ids": [seats[0]["id"]]})
    assert r.status_code == 401
