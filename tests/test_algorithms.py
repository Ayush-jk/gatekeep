import asyncio
import uuid

import pytest

from service import limiter


def unique_key() -> str:
    return uuid.uuid4().hex


@pytest.mark.asyncio
async def test_token_bucket_allows_up_to_capacity_then_blocks():
    key = unique_key()
    results = [await limiter.check("token_bucket", key, 5, 10) for _ in range(6)]
    assert [r["allowed"] for r in results] == [True, True, True, True, True, False]


@pytest.mark.asyncio
async def test_token_bucket_refills_over_time():
    key = unique_key()
    for _ in range(5):
        await limiter.check("token_bucket", key, 5, 1)  # drain the bucket, refill rate 5/s
    assert (await limiter.check("token_bucket", key, 5, 1))["allowed"] is False
    await asyncio.sleep(1.1)
    assert (await limiter.check("token_bucket", key, 5, 1))["allowed"] is True


@pytest.mark.asyncio
async def test_sliding_window_log_is_exact():
    key = unique_key()
    results = [await limiter.check("sliding_window_log", key, 4, 5) for _ in range(6)]
    assert sum(r["allowed"] for r in results) == 4


@pytest.mark.asyncio
async def test_sliding_window_log_expires_old_entries():
    key = unique_key()
    for _ in range(3):
        await limiter.check("sliding_window_log", key, 3, 1)
    assert (await limiter.check("sliding_window_log", key, 3, 1))["allowed"] is False
    await asyncio.sleep(1.1)
    assert (await limiter.check("sliding_window_log", key, 3, 1))["allowed"] is True


@pytest.mark.asyncio
async def test_sliding_window_counter_blocks_past_limit():
    key = unique_key()
    results = [await limiter.check("sliding_window_counter", key, 4, 5) for _ in range(6)]
    assert sum(r["allowed"] for r in results) == 4


@pytest.mark.asyncio
async def test_naive_blocks_past_limit_within_one_process():
    key = unique_key()
    results = [await limiter.check("naive", key, 4, 5) for _ in range(6)]
    assert sum(r["allowed"] for r in results) == 4
