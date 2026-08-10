"""
Sliding window counter. Splits time into fixed buckets and estimates the
current count as a weighted blend of the previous bucket and the current
one, weighted by how far into the current bucket we are. One integer per
bucket per key, regardless of request rate - constant memory, unlike the
log - but the count is an approximation, not exact.
"""

from pathlib import Path
from time import time

from redis.asyncio import Redis

from ..redis_client import eval_script

_SCRIPT = (Path(__file__).resolve().parent.parent / "lua" / "sliding_window_counter.lua").read_text()


async def check(client: Redis, key: str, limit: int, window_seconds: float) -> dict:
    allowed, estimate = await eval_script(
        client, _SCRIPT, 1, f"swc:{key}", time(), window_seconds, limit
    )
    return {"allowed": bool(int(allowed)), "estimate": float(estimate)}
