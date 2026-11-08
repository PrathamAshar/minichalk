"""Run from backend: uv run python ../benchmarks/run.py --iterations 20."""

import argparse
import asyncio
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.engine.executor import Executor  # noqa: E402
from app.features.fraud import build_registry  # noqa: E402
from app.sources.database import Database  # noqa: E402
from app.sources.demo import DemoSources  # noqa: E402


async def benchmark(iterations: int) -> dict:
    db = Database(":memory:")
    await db.open()
    report = {"iterations": iterations, "units": "milliseconds", "workloads": {}}
    try:
        for workload, delay in [
            ("artificial_io_120ms", 0.12),
            ("local_sqlite_no_artificial_io", 0.0),
        ]:
            modes = {}
            for mode, concurrency, warm in [
                ("sequential_cold", 1, False),
                ("concurrent_cold", 8, False),
                ("concurrent_warm", 8, True),
            ]:
                engine = Executor(
                    build_registry(),
                    sources=DemoSources(db, delay),
                    concurrency=concurrency,
                )
                if warm:
                    await engine.query("usr_nova", ["user.fraud_score"])
                timings, executed, hits, lookups = [], 0, 0, 0
                for _ in range(iterations):
                    if not warm:
                        engine.cache.invalidate(set(engine.registry.features))
                    trace = await engine.query("usr_nova", ["user.fraud_score"])
                    assert trace.status == "success", trace.error
                    timings.append(trace.duration_ms)
                    executed += sum(s.cache in ("miss", "bypass") for s in trace.spans)
                    hits += sum(s.cache in ("hit", "coalesced") for s in trace.spans)
                    lookups += len(trace.spans)
                modes[mode] = {
                    "median_ms": round(statistics.median(timings), 3),
                    "p95_ms": round(sorted(timings)[math.ceil(0.95 * iterations) - 1], 3),
                    "executed_features_per_query": executed / iterations,
                    "cache_hit_rate": hits / lookups,
                }
            baseline = modes["sequential_cold"]["median_ms"]
            for value in modes.values():
                value["speedup_vs_sequential_cold"] = round(baseline / value["median_ms"], 2)
            report["workloads"][workload] = modes
    finally:
        await db.close()
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks" / "results.json")
    args = parser.parse_args()
    if args.iterations < 2:
        parser.error("Use at least two iterations")
    result = asyncio.run(benchmark(args.iterations))
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
