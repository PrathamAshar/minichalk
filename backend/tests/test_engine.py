import asyncio

import pytest

from app.engine.cache import Cache
from app.engine.executor import Executor
from app.engine.registry import Registry


def diamond():
    r = Registry()
    calls = []

    @r.feature("a", ttl_seconds=30)
    async def a(ctx) -> int:
        calls.append("a")
        return 2

    @r.feature("b", dependencies=["a"], ttl_seconds=30)
    async def b(ctx, deps) -> int:
        calls.append("b")
        return deps["a"] + 1

    @r.feature("c", dependencies=["a"], ttl_seconds=30)
    async def c(ctx, deps) -> int:
        calls.append("c")
        return deps["a"] * 2

    @r.feature("d", dependencies=["b", "c"], ttl_seconds=30)
    async def d(ctx, deps) -> int:
        calls.append("d")
        return deps["b"] + deps["c"]

    return r, calls


def test_registration_and_deterministic_plan():
    r, _ = diamond()
    assert r.plan(["d"])["order"] == ["a", "b", "c", "d"]
    assert r.plan(["d"])["layers"] == [["a"], ["b", "c"], ["d"]]
    assert r.features["a"].metadata()["output_type"] == {"type": "integer"}
    with pytest.raises(ValueError, match="Duplicate"):
        r.feature("a")(r.features["a"].fn)


def test_missing_and_cycles():
    r = Registry()

    @r.feature("a", dependencies=["b"])
    async def a(ctx, deps):
        return 1

    with pytest.raises(ValueError, match="Missing feature: b"):
        r.validate()

    @r.feature("b", dependencies=["a"])
    async def b(ctx, deps):
        return 2

    with pytest.raises(ValueError, match="a -> b -> a"):
        r.validate()


async def test_diamond_and_multiple_outputs():
    r, calls = diamond()
    result = await Executor(r).query("u", ["d", "b"])
    assert result.results == {"b": 3, "d": 7}
    assert calls.count("a") == 1
    assert calls.index("a") < calls.index("b") < calls.index("d")
    assert calls.index("c") < calls.index("d")
    assert len(result.spans) == 4
    assert result.status == "success"
    assert result.started_at < result.ended_at
    assert all(s.start_ms <= s.end_ms <= result.duration_ms for s in result.spans)
    assert result.critical_path[0] == "a" and result.critical_path[-1] == "d"


async def test_disconnected_outputs():
    r, _ = diamond()

    @r.feature("z")
    async def z(ctx) -> int:
        return 99

    trace = await Executor(r).query("u", ["b", "z"])
    assert trace.results == {"b": 3, "z": 99}
    assert trace.graph.order == ["a", "b", "z"]


async def test_independent_features_overlap_without_sleep():
    r = Registry()
    started = {n: asyncio.Event() for n in ["a", "b"]}

    @r.feature("a")
    async def a(ctx) -> int:
        started["a"].set()
        await started["b"].wait()
        return 1

    @r.feature("b")
    async def b(ctx) -> int:
        started["b"].set()
        await started["a"].wait()
        return 2

    trace = await Executor(r, concurrency=2).query("u", ["a", "b"], timeout_seconds=0.5)
    assert trace.status == "success"
    a_span, b_span = trace.spans
    assert max(a_span.start_ms, b_span.start_ms) < min(a_span.end_ms, b_span.end_ms)


async def test_cache_ttl_parameters_entity_bypass_and_invalidation():
    clock = [0.0]
    cache = Cache(clock=lambda: clock[0])
    r, calls = diamond()
    e = Executor(r, cache)
    first = await e.query("u", ["d"])
    assert all(s.cache == "miss" for s in first.spans)
    second = await e.query("u", ["d"])
    assert all(s.cache == "hit" for s in second.spans)
    assert len(calls) == 4
    await e.query("other", ["d"])
    await e.query("u", ["d"], {"amount": 1})
    assert len(calls) == 12
    await e.query("u", ["d"], bypass_cache=True)
    assert len(calls) == 16
    clock[0] = 31
    await e.query("u", ["d"])
    assert len(calls) == 20
    assert cache.invalidate(r.affected("a"), "u") == 8
    assert all(k[1] != "u" for k in cache.entries)
    await e.query("u", ["d"])
    assert len(calls) == 24


async def test_singleflight_and_no_lock_leaks():
    r = Registry()
    calls = 0
    started, release = asyncio.Event(), asyncio.Event()

    @r.feature("x", ttl_seconds=30)
    async def x(ctx) -> int:
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        return 42

    e = Executor(r)
    first = asyncio.create_task(e.query("u", ["x"]))
    await started.wait()
    second = asyncio.create_task(e.query("u", ["x"]))
    # Advance second to its lock wait without timing-based assertions.
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    release.set()
    traces = await asyncio.gather(first, second)
    assert calls == 1
    assert [t.results for t in traces] == [{"x": 42}] * 2
    assert traces[1].spans[0].cache == "coalesced"
    assert not e.cache.locks


async def test_failure_cancels_sibling_and_never_runs_dependent():
    r = Registry()
    started, cleaned = asyncio.Event(), asyncio.Event()
    dependent_called = False

    @r.feature("a")
    async def a(ctx) -> int:
        await started.wait()
        raise RuntimeError("source unavailable")

    @r.feature("b")
    async def b(ctx) -> int:
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()
        return 1

    @r.feature("c", dependencies=["a"])
    async def c(ctx, deps) -> int:
        nonlocal dependent_called
        dependent_called = True
        return 1

    e = Executor(r)
    trace = await e.query("u", ["b", "c"])
    assert trace.status == "failed"
    assert "source unavailable" in trace.error
    assert cleaned.is_set() and not dependent_called
    assert not trace.results and not e.cache.entries
    assert all(s.status not in ("running", "waiting") for s in trace.spans)


async def test_timeout_and_cancellation_cleanup():
    r = Registry()
    started, cleaned = asyncio.Event(), asyncio.Event()

    @r.feature("slow", ttl_seconds=10)
    async def slow(ctx) -> int:
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()
        return 0

    e = Executor(r)
    trace = await e.query("u", ["slow"], timeout_seconds=0.02)
    assert trace.status == "timeout" and cleaned.is_set()
    cleaned.clear()
    started.clear()
    stored = []

    class Store:
        async def save_trace(self, trace):
            stored.append(trace)

    task = asyncio.create_task(e.query("u", ["slow"], store=Store()))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cleaned.is_set() and not e.cache.locks and not e.cache.entries
    assert stored[0].status == "cancelled"


async def test_output_validation():
    r = Registry()

    @r.feature("bad", ttl_seconds=30)
    async def bad(ctx) -> int:
        return "not an integer"

    e = Executor(r)
    trace = await e.query("u", ["bad"])
    assert trace.status == "failed" and not e.cache.entries


async def test_invalidation_fences_inflight_writes():
    r = Registry()
    started, release = asyncio.Event(), asyncio.Event()

    @r.feature("x", ttl_seconds=30)
    async def x(ctx) -> int:
        started.set()
        await release.wait()
        return 1

    e = Executor(r)
    task = asyncio.create_task(e.query("u", ["x"]))
    await started.wait()
    e.cache.invalidate({"x"})
    release.set()
    assert (await task).status == "success"
    assert not e.cache.entries


async def test_bounded_concurrency():
    r = Registry()
    active = 0
    peak = 0

    async def work(ctx) -> int:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0)
        active -= 1
        return 1

    for name in ["a", "b", "c", "d"]:
        r.feature(name)(work)
    trace = await Executor(r, concurrency=2).query("u", list(r.features))
    assert trace.status == "success" and peak == 2


async def test_cache_values_isolated_and_capacity_bounded():
    cache = Cache(max_entries=1)
    key = ("a", "u", "{}", "1")
    cache.put(key, {"x": []}, 30, 0)
    cache.get(key)[1]["x"].append(1)
    assert cache.get(key)[1] == {"x": []}
    cache.put(("b", "u", "{}", "1"), 3, 30, 0)
    assert not cache.get(key)[0]


async def test_definition_version_invalidates_transitive_outputs():
    from dataclasses import replace

    r, calls = diamond()
    e = Executor(r)
    await e.query("u", ["d"])
    r.features["a"] = replace(r.features["a"], version="2")
    trace = await e.query("u", ["d"])
    assert trace.status == "success"
    assert len(calls) == 8
    assert all(span.cache == "miss" for span in trace.spans)


async def test_singleflight_waiter_recovers_from_cancelled_producer():
    r = Registry()
    entered = asyncio.Event()
    calls = 0

    @r.feature("x", ttl_seconds=30)
    async def x(ctx) -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            entered.set()
            await asyncio.Event().wait()
        return 7

    e = Executor(r)
    first = asyncio.create_task(e.query("u", ["x"]))
    await entered.wait()
    second = asyncio.create_task(e.query("u", ["x"]))
    await asyncio.sleep(0)
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    trace = await second
    assert trace.results == {"x": 7} and calls == 2
    assert not e.cache.locks
