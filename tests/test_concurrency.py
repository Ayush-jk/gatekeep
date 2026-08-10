"""
Two things worth proving separately:

1. The Redis-backed algorithms stay correct under real concurrent load -
   firing many requests at once shouldn't let the count sneak past the
   limit just because requests overlap.

2. That correctness isn't free. A naive "GET count, compare, INCR"
   implementation - two round trips, no atomicity - looks identical to
   the Lua version when tested one request at a time, but overshoots
   the limit under concurrency because two requests can both read the
   same count before either writes it back. This reproduces that race
   to show why the Lua script (a single atomic round trip) is the part
   that actually matters, not just "uses Redis".
"""

import asyncio
import uuid

import pytest

from service import limiter
from service.redis_client import get_redis


def unique_key() -> str:
    return uuid.uuid4().hex


@pytest.mark.asyncio
async def test_sliding_window_log_holds_limit_under_concurrency():
    key = unique_key()
    limit = 10
    results = await asyncio.gather(
        *[limiter.check("sliding_window_log", key, limit, 5) for _ in range(50)]
    )
    assert sum(r["allowed"] for r in results) == limit


@pytest.mark.asyncio
async def test_token_bucket_holds_capacity_under_concurrency():
    key = unique_key()
    capacity = 10
    results = await asyncio.gather(
        *[limiter.check("token_bucket", key, capacity, 5) for _ in range(50)]
    )
    assert sum(r["allowed"] for r in results) == capacity


async def _non_atomic_check(client, key: str, limit: int) -> bool:
    """Deliberately broken: read-then-write across two round trips, no lock."""
    count = int(await client.get(key) or 0)
    if count >= limit:
        return False
    await client.incr(key)
    return True


@pytest.mark.asyncio
async def test_non_atomic_get_then_incr_overshoots_under_concurrency():
    client = get_redis()
    key = f"race-demo:{unique_key()}"
    limit = 10

    results = await asyncio.gather(*[_non_atomic_check(client, key, limit) for _ in range(50)])
    allowed_count = sum(results)

    # This is the bug the Lua scripts exist to prevent: concurrent requests
    # can all read the count before any of them writes it back, so more
    # than `limit` requests get through.
    assert allowed_count > limit
