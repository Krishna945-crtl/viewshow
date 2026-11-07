"""Temporary seat holds in Redis.

Keys use a {show} hash tag so everything for one show lives in one cluster slot
and the Lua scripts stay atomic.

    cv:{show}:seat:<seat>   -> user id (PX = time left in the hold session)
    cv:{show}:sess:<user>   -> deadline (ms). first hold starts the 5 min clock,
                               adding seats does NOT extend it
    cv:{show}:mine:<user>   -> set of seats the user holds
    cv:{show}:exp           -> zset seat -> deadline, used by the sweeper
    cv:holdshows            -> shows that have live holds
"""

import time
from dataclasses import dataclass

from redis.asyncio import Redis

from app.core.config import get_settings

HOLD_LUA = """
local sess, mine, exp = KEYS[1], KEYS[2], KEYS[3]
local user, now, ttl, max_seats = ARGV[1], tonumber(ARGV[2]), tonumber(ARGV[3]), tonumber(ARGV[4])
local prefix = ARGV[5]

local deadline = tonumber(redis.call('GET', sess) or '0')
if deadline <= now then
  deadline = now + ttl
  redis.call('DEL', mine)
end
local left = deadline - now

-- prune seats that quietly expired / got released
local held = redis.call('SMEMBERS', mine)
local count = 0
for _, s in ipairs(held) do
  if redis.call('GET', prefix .. s) == user then count = count + 1 else redis.call('SREM', mine, s) end
end

local fresh = 0
for i = 6, #ARGV do
  local owner = redis.call('GET', prefix .. ARGV[i])
  if owner and owner ~= user then return {-1, ARGV[i]} end
  if not owner then fresh = fresh + 1 end
end
if count + fresh > max_seats then return {-2, tostring(max_seats)} end

redis.call('SET', sess, deadline, 'PX', left)
for i = 6, #ARGV do
  redis.call('SET', prefix .. ARGV[i], user, 'PX', left)
  redis.call('SADD', mine, ARGV[i])
  redis.call('ZADD', exp, deadline, ARGV[i])
end
redis.call('PEXPIRE', mine, left)
return {1, tostring(deadline)}
"""

RELEASE_LUA = """
local mine, exp, user, prefix = KEYS[1], KEYS[2], ARGV[1], ARGV[2]
local out = {}
for i = 3, #ARGV do
  local k = prefix .. ARGV[i]
  if redis.call('GET', k) == user then
    redis.call('DEL', k)
    redis.call('SREM', mine, ARGV[i])
    redis.call('ZREM', exp, ARGV[i])
    table.insert(out, ARGV[i])
  end
end
return out
"""

SHOWS_KEY = "cv:holdshows"


def _k(show_id: str) -> str:
    return f"cv:{{{show_id}}}:"


@dataclass
class HoldResult:
    ok: bool
    deadline_ms: int = 0
    conflict_seat: str | None = None
    too_many: bool = False


class HoldStore:
    def __init__(self, redis: Redis):
        self.r = redis
        self._hold = redis.register_script(HOLD_LUA)
        self._release = redis.register_script(RELEASE_LUA)

    async def hold(self, show_id: str, user_id: str, seat_ids: list[str], ttl_s: int | None = None) -> HoldResult:
        s = get_settings()
        ttl_ms = int((ttl_s or s.hold_seconds) * 1000)
        p = _k(show_id)
        now = int(time.time() * 1000)
        res = await self._hold(
            keys=[p + f"sess:{user_id}", p + f"mine:{user_id}", p + "exp"],
            args=[user_id, now, ttl_ms, s.max_seats_per_booking, p + "seat:", *seat_ids],
        )
        code, info = int(res[0]), res[1]
        if code == -1:
            return HoldResult(False, conflict_seat=info)
        if code == -2:
            return HoldResult(False, too_many=True)
        await self.r.sadd(SHOWS_KEY, show_id)
        return HoldResult(True, deadline_ms=int(info))

    async def release(self, show_id: str, user_id: str, seat_ids: list[str]) -> list[str]:
        if not seat_ids:
            return []
        p = _k(show_id)
        return list(await self._release(keys=[p + f"mine:{user_id}", p + "exp"], args=[user_id, p + "seat:", *seat_ids]))

    async def release_all(self, show_id: str, user_id: str) -> list[str]:
        mine = await self.user_holds(show_id, user_id)
        return await self.release(show_id, user_id, mine)

    async def user_holds(self, show_id: str, user_id: str) -> list[str]:
        p = _k(show_id)
        members = await self.r.smembers(p + f"mine:{user_id}")
        if not members:
            return []
        members = sorted(members)
        owners = await self.r.mget([p + "seat:" + m for m in members])
        return [m for m, o in zip(members, owners) if o == user_id]

    async def deadline(self, show_id: str, user_id: str) -> int | None:
        v = await self.r.get(_k(show_id) + f"sess:{user_id}")
        return int(v) if v else None

    async def owners(self, show_id: str, seat_ids: list[str] | None = None) -> dict[str, str]:
        """seat -> owner user id, for every live hold (or just the given seats)."""
        p = _k(show_id)
        if seat_ids is None:
            seat_ids = await self.r.zrange(p + "exp", 0, -1)
        if not seat_ids:
            return {}
        vals = await self.r.mget([p + "seat:" + s for s in seat_ids])
        return {s: v for s, v in zip(seat_ids, vals) if v}

    async def sweep(self) -> dict[str, list[str]]:
        """Find holds that expired since last sweep. Returns show -> seats freed."""
        now = int(time.time() * 1000)
        freed: dict[str, list[str]] = {}
        for show_id in await self.r.smembers(SHOWS_KEY):
            p = _k(show_id)
            due = await self.r.zrangebyscore(p + "exp", "-inf", now)
            if due:
                vals = await self.r.mget([p + "seat:" + s for s in due])
                gone = [s for s, v in zip(due, vals) if v is None]
                if gone:
                    await self.r.zrem(p + "exp", *gone)
                    freed[show_id] = gone
            if await self.r.zcard(p + "exp") == 0:
                await self.r.srem(SHOWS_KEY, show_id)
        return freed
