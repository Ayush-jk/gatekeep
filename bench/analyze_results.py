"""
Reads a results JSON file from load_test.py and prints how well the
run matched the configured limit, plus latency percentiles and a
per-instance breakdown - that per-instance split is what makes the
naive algorithm's over-permit visible.

Usage: python bench/analyze_results.py bench/results/token_bucket.json
"""

import argparse
import json
from collections import Counter


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = min(len(values) - 1, int(len(values) * p))
    return values[idx]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()

    data = json.loads(open(args.path).read())
    cfg = data["args"]
    results = data["results"]

    errors = [r for r in results if r.get("allowed") is None]
    completed = [r for r in results if r.get("allowed") is not None]
    allowed = [r for r in completed if r["allowed"]]
    latencies = [r["latency_ms"] for r in completed]

    configured_limit = cfg["limit"]
    over_permit_pct = ((len(allowed) - configured_limit) / configured_limit) * 100

    print(f"algorithm:        {cfg['algorithm']}")
    print(f"instances:        {len(cfg['instances'])}")
    print(f"requests sent:    {len(results)} ({errors and len(errors) or 0} errors)")
    print(f"configured limit: {configured_limit} per {cfg['window']}s")
    print(f"allowed:          {len(allowed)}")
    print(f"over-permit:      {over_permit_pct:+.1f}%  (0% is exact)")
    print()
    print(f"latency p50:      {percentile(latencies, 0.50):.2f} ms")
    print(f"latency p95:      {percentile(latencies, 0.95):.2f} ms")
    print(f"latency p99:      {percentile(latencies, 0.99):.2f} ms")

    per_instance = Counter(r["url"] for r in allowed)
    if len(per_instance) > 1:
        print()
        print("allowed per instance:")
        for url, count in per_instance.items():
            print(f"  {url}: {count}")


if __name__ == "__main__":
    main()
