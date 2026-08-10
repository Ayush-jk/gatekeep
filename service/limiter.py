from .algorithms import naive, sliding_window_counter, sliding_window_log, token_bucket
from .redis_client import get_redis

NEEDS_REDIS = {"token_bucket", "sliding_window_log", "sliding_window_counter"}

_ALGORITHMS = {
    "naive": naive.check,
    "token_bucket": token_bucket.check,
    "sliding_window_log": sliding_window_log.check,
    "sliding_window_counter": sliding_window_counter.check,
}


async def check(algorithm: str, key: str, limit: int, window_seconds: float) -> dict:
    if algorithm not in _ALGORITHMS:
        raise ValueError(f"unknown algorithm: {algorithm}")

    fn = _ALGORITHMS[algorithm]
    if algorithm in NEEDS_REDIS:
        return await fn(get_redis(), key, limit, window_seconds)
    return await fn(key, limit, window_seconds)
