"""
Token bucket. A bucket holds up to `limit` tokens and refills at
limit/window_seconds tokens per second. Each request costs one token.
Allows short bursts up to the bucket size, then throttles to the steady
refill rate. State lives in Redis so every instance shares one bucket
per key, and the read-modify-write happens inside a Lua script so
concurrent requests can't race past the limit.
"""

from pathlib import Path
from time import time

from redis.asyncio import Redis

from ..redis_client import eval_script

_SCRIPT = (Path(__file__).resolve().parent.parent / "lua" / "token_bucket.lua").read_text()


async def check(client: Redis, key: str, limit: int, window_seconds: float) -> dict:
    refill_rate = limit / window_seconds
    allowed, remaining = await eval_script(
        client, _SCRIPT, 1, f"tb:{key}", limit, refill_rate, time(), 1
    )
    return {"allowed": bool(int(allowed)), "remaining_tokens": float(remaining)}
