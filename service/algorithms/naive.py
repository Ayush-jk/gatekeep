"""
Fixed-window counter kept in local process memory, one window per key,
anchored to that key's first request rather than to wall-clock time.
Correct within a single process, but each process has its own counters,
so it does not know about requests handled by other instances. That's
the bug this project measures: run this behind N instances and the
effective cluster limit becomes roughly N times the configured one.
"""

import threading
import time

_lock = threading.Lock()
_windows: dict[str, tuple[float, int]] = {}  # key -> (window_start, count)


async def check(key: str, limit: int, window_seconds: float) -> dict:
    now = time.time()

    with _lock:
        window_start, count = _windows.get(key, (now, 0))
        if now - window_start >= window_seconds:
            window_start = now
            count = 0

        allowed = count < limit
        if allowed:
            count += 1
        _windows[key] = (window_start, count)

    return {"allowed": allowed, "count": count}