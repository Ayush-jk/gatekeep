# Distributed Rate Limiter

A rate-limiting service that stays correct when it's running on more than one
instance. The actual problem this project is about: a rate limiter that keeps
its counters in local process memory is correct on one instance and silently
wrong on three - each instance enforces the limit independently, so the
effective limit across the cluster becomes roughly (limit × instance count).
This project implements four algorithms, runs all of them behind a 3-instance
cluster under identical load, and measures which ones actually hold the
configured limit and which ones don't - with real numbers, not just an
assertion.

## The result the whole project is built to demonstrate

3 instances, one Redis, `limit=60 requests / 60s`, driven with sustained load
well above the limit (10 req/s for 30s, round-robin across the 3 instances):

| Algorithm | Allowed | Over-permit | Notes |
|---|---|---|---|
| naive (in-memory, per-process) | 180 | **+200%** | exactly 60 per instance - three independent limits |
| sliding window log | 60 | **0%** | exact, shared state via Redis |
| sliding window counter | 71 | +18% | shared state, but fixed-bucket approximation |
| token bucket | 90 | +50% | by design, not a bug - see below |

Raw request-level results for each run are in `bench/results/*.json`.

The naive algorithm allowing *exactly* 60 per instance (180 total) is the
whole point: it isn't randomly wrong, it's deterministically wrong in the way
you'd expect once you see how it's implemented - see `service/algorithms/naive.py`.
Token bucket's 90 is also deterministic, reproducible on every run, because
it's a fixed formula (below). Sliding window counter's overshoot varies run
to run (66-71 across repeated tests here) because it depends on whether the
test happens to straddle a fixed bucket boundary - see below.

### Why token bucket shows +50%, and why that isn't a bug

Token bucket doesn't guarantee "at most N per window" - it guarantees a burst
allowance (capacity) plus a steady refill rate. With capacity=60 and
refill=1 token/sec, a 30-second test under sustained overload allows
`capacity + refill_rate × duration = 60 + 1×30 = 90` - which is exactly what
was measured. It's a different contract than the windowed algorithms, useful
when you want to allow bursts, not a correctness bug.

### Why sliding window counter overshoots by a variable amount

It approximates the current count as a weighted blend of the current fixed
bucket and the previous one, which is O(1) memory per key but ties bucket
boundaries to wall-clock time rather than the request's own arrival time.
If a test run happens to straddle one of those bucket boundaries, a few extra
requests land in the fresh bucket before it fills. Sliding window log doesn't
have this failure mode because it has no fixed boundaries at all - every
request looks back exactly `window_seconds` from its own arrival time.

### Memory cost per key, measured with `MEMORY USAGE` after the same load

| Algorithm | Bytes per key | Scales with |
|---|---|---|
| token bucket | 152 | nothing - fixed hash, O(1) |
| sliding window counter | 104 | nothing - one integer, O(1) |
| sliding window log | 3160 (60 entries) | request count within the window, O(n) |

Sliding window log is the only one of the three that's exact, and it pays for
that with memory proportional to request rate. That's the real tradeoff
between these algorithms - not a "which one is best" question, a "what are
you optimizing for" one.

## Why atomicity matters, proven by breaking it on purpose

All three Redis-backed algorithms run as a single Lua script per check - one
round trip, so concurrent requests can't race. `tests/test_concurrency.py`
proves this holds under 50 concurrent requests, then reproduces the bug a
naive `GET count, compare, INCR` implementation (two round trips, no lock)
would have: fired concurrently, it lets more requests through than the limit,
because two requests can both read the same count before either writes it
back. Run it:

```
pytest tests/test_concurrency.py -v
```

## Algorithms

- **Naive (in-memory)** - `service/algorithms/naive.py`. Correct within a
  single process. The broken baseline for the horizontal-scaling test.
- **Token bucket** - `service/algorithms/token_bucket.py` +
  `service/lua/token_bucket.lua`. Capacity + steady refill rate, allows bursts.
- **Sliding window log** - `service/algorithms/sliding_window_log.py` +
  `service/lua/sliding_window_log.lua`. Exact, O(n) memory (Redis sorted set).
- **Sliding window counter** - `service/algorithms/sliding_window_counter.py`
  + `service/lua/sliding_window_counter.lua`. Approximate, O(1) memory.

All four share one interface: `check(key, limit, window_seconds) -> {allowed, ...}`,
dispatched in `service/limiter.py`.

## Running it

```
docker compose up --build
```

Brings up Redis and 3 instances of the service on ports 9001-9003, all
pointed at the same Redis.

Or without Docker:

```
pip install -r requirements.txt
redis-server &
INSTANCE_NAME=instance-1 uvicorn service.main:app --port 9001 &
INSTANCE_NAME=instance-2 uvicorn service.main:app --port 9002 &
INSTANCE_NAME=instance-3 uvicorn service.main:app --port 9003 &
```

Check a request:

```
curl -X POST http://localhost:9001/check \
  -H "Content-Type: application/json" \
  -d '{"key": "user-42", "algorithm": "token_bucket", "limit": 60, "window_seconds": 60}'
```

## Reproducing the benchmark

```
python bench/load_test.py --algorithm naive \
  --instances http://localhost:9001 http://localhost:9002 http://localhost:9003 \
  --rate 10 --duration 30 --limit 60 --window 60

python bench/analyze_results.py bench/results/naive.json
```

Swap `--algorithm` for `token_bucket`, `sliding_window_log`, or
`sliding_window_counter` to compare. `analyze_results.py` prints allowed
count vs configured limit, latency percentiles, and a per-instance
breakdown - that breakdown is what makes the naive algorithm's failure
mode visible.

## Tests

```
pytest tests/ -v
```

`test_algorithms.py` covers per-algorithm correctness (burst limits, refill,
expiry). `test_concurrency.py` covers the atomicity proof above.
