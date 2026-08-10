"""
Fires requests at a fixed rate against a rate-limited key, spread round-robin
across however many service instances are given, and writes every response
(allowed/denied, latency, which instance) to a JSON file for analyze_results.py
to score.

Usage:
    python bench/load_test.py --algorithm token_bucket --instances \
        http://localhost:9001 http://localhost:9002 http://localhost:9003 \
        --rate 10 --duration 30 --limit 60 --window 60
"""

import argparse
import asyncio
import json
import time
from pathlib import Path

import httpx


async def fire(client: httpx.AsyncClient, url: str, key: str, algorithm: str, limit: int, window: float):
    start = time.perf_counter()
    try:
        resp = await client.post(
            f"{url}/check",
            json={"key": key, "algorithm": algorithm, "limit": limit, "window_seconds": window},
            timeout=5,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        body = resp.json()
        return {
            "t": time.time(),
            "url": url,
            "allowed": body["allowed"],
            "latency_ms": latency_ms,
            "status": resp.status_code,
        }
    except Exception as e:
        return {
            "t": time.time(),
            "url": url,
            "allowed": None,
            "latency_ms": (time.perf_counter() - start) * 1000,
            "error": str(e),
        }


async def run(args) -> list[dict]:
    key = f"bench:{args.algorithm}:{int(time.time())}"
    interval = 1.0 / args.rate
    total_requests = int(args.rate * args.duration)

    results = []
    async with httpx.AsyncClient() as client:
        tasks = []
        for i in range(total_requests):
            instance = args.instances[i % len(args.instances)]
            tasks.append(
                asyncio.create_task(
                    fire(client, instance, key, args.algorithm, args.limit, args.window)
                )
            )
            await asyncio.sleep(interval)
        results = await asyncio.gather(*tasks)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--algorithm", required=True)
    parser.add_argument("--instances", nargs="+", required=True)
    parser.add_argument("--rate", type=float, default=10.0, help="requests per second")
    parser.add_argument("--duration", type=float, default=30.0, help="seconds")
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--window", type=float, default=60.0)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    results = asyncio.run(run(args))

    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    out_path = Path(args.out) if args.out else out_dir / f"{args.algorithm}.json"
    out_path.write_text(json.dumps({"args": vars(args), "results": results}, indent=2))
    print(f"wrote {len(results)} results to {out_path}")


if __name__ == "__main__":
    main()
