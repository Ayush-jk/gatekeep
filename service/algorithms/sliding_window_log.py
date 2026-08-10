"""
Sliding window log. Every allowed request's timestamp is stored in a
Redis sorted set; on each check, entries older than the window are
trimmed and the remaining count is compared to the limit. Exact - no
approximation error - at the cost of one sorted-set entry per request
for the length of the window.
"""

import uuid
from pathlib import Path
from time import time

from redis.asyncio import Redis

from ..redis_client import eval_script

_SCRIPT = (Path(__file__).resolve().parent.parent / "lua" / "sliding_window_log.lua").read_text()


async def check(client: Redis, key: str, limit: int, window_seconds: float) -> dict:
    now = time()
    member = f"{now}-{uuid.uuid4().hex[:8]}"
    allowed, count = await eval_script(
        client, _SCRIPT, 1, f"swl:{key}", now, window_seconds, limit, member
    )
    return {"allowed": bool(int(allowed)), "count": int(count)}
