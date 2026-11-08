"""One task per plan node. Dependency waits never consume compute permits."""

import asyncio
import hashlib
import json
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.engine.cache import Cache
from app.engine.registry import Registry
from app.engine.tracing import Span, Trace


@dataclass(frozen=True)
class Context:
    entity_id: str
    parameters: dict[str, Any]
    sources: Any = None


@asynccontextmanager
async def no_lock():
    yield


class Executor:
    def __init__(
        self,
        registry: Registry,
        cache: Cache | None = None,
        sources: Any = None,
        concurrency: int = 8,
    ):
        if concurrency < 1:
            raise ValueError("Concurrency must be positive")
        self.registry = registry
        self.cache = cache if cache is not None else Cache()
        self.sources = sources
        self.semaphore = asyncio.Semaphore(concurrency)

    async def query(
        self,
        entity_id: str,
        requested: list[str],
        parameters: dict[str, Any] | None = None,
        bypass_cache: bool = False,
        timeout_seconds: float = 5,
        store: Any = None,
    ) -> Trace:
        graph = self.registry.plan(requested)
        params = parameters or {}
        serialized = json.dumps(params, sort_keys=True, separators=(",", ":"), allow_nan=False)
        start = time.monotonic()
        trace = Trace(
            query_id=str(uuid.uuid4()),
            entity_id=entity_id,
            requested=graph["requested"],
            parameters=params,
            started_at=datetime.now(UTC).isoformat(),
            graph=graph,
            spans=[
                Span(name=n, dependencies=list(self.registry.features[n].dependencies))
                for n in graph["order"]
            ],
        )
        spans = {s.name: s for s in trace.spans}
        tasks: dict[str, asyncio.Task[Any]] = {}
        # Include transitive versions so changing a leaf invalidates cached derived outputs.
        signatures: dict[str, str] = {}
        for name in graph["order"]:
            f = self.registry.features[name]
            signatures[name] = hashlib.sha256(
                json.dumps(
                    [name, f.version, [signatures[d] for d in f.dependencies]],
                ).encode()
            ).hexdigest()
        generation = self.cache.generation

        def elapsed() -> float:
            return (time.monotonic() - start) * 1000

        async def run(name: str) -> Any:
            f = self.registry.features[name]
            span = spans[name]
            key = (name, entity_id, serialized, signatures[name])
            try:
                # Resolve every prerequisite before reporting dependent success, even on a hit.
                deps = {d: await tasks[d] for d in f.dependencies}
                if not bypass_cache:
                    hit, value = self.cache.get(key)
                    if hit:
                        span.cache = "hit"
                        span.status = "success"
                        span.start_ms = span.end_ms = elapsed()
                        return value
                span.cache = "bypass" if bypass_cache else "miss"
                lock = (
                    no_lock()
                    if bypass_cache or f.ttl_seconds <= 0
                    else self.cache.singleflight(key)
                )
                async with lock:
                    if not bypass_cache:
                        hit, value = self.cache.get(key)
                        if hit:
                            span.cache = "coalesced"
                            span.status = "success"
                            span.start_ms = span.end_ms = elapsed()
                            return value
                    async with self.semaphore:
                        span.start_ms = elapsed()
                        span.status = "running"
                        # Each computation receives isolated JSON parameters and dependency values.
                        import copy

                        ctx = Context(entity_id, json.loads(serialized), self.sources)
                        value = await (
                            f.fn(ctx, copy.deepcopy(deps)) if f.dependencies else f.fn(ctx)
                        )
                        value = f.adapter.validate_python(value, strict=True)
                        # Check serializability before caching or returning success.
                        value = f.adapter.dump_python(value, mode="json")
                        json.dumps(value, allow_nan=False)
                        if not bypass_cache:
                            self.cache.put(key, value, f.ttl_seconds, generation)
                        span.status = "success"
                        return value
            except asyncio.CancelledError:
                span.status = "cancelled" if span.start_ms is not None else "skipped"
                raise
            except Exception as exc:
                span.status = "failed"
                span.error = f"{type(exc).__name__}: {exc}"
                raise
            finally:
                if span.start_ms is not None and span.end_ms is None:
                    span.end_ms = elapsed()
                    span.duration_ms = span.end_ms - span.start_ms

        try:
            async with asyncio.timeout(timeout_seconds):
                async with asyncio.TaskGroup() as group:
                    for name in graph["order"]:
                        tasks[name] = group.create_task(run(name), name=name)
                trace.results = {n: tasks[n].result() for n in graph["requested"]}
                trace.status = "success"
        except TimeoutError:
            trace.status, trace.error = "timeout", "Query deadline exceeded"
        except asyncio.CancelledError:
            trace.status, trace.error = "cancelled", "Query cancelled"
            raise
        except Exception as exc:
            trace.status, trace.error = "failed", str(exc)
            errors = [s.error for s in trace.spans if s.error]
            if errors:
                trace.error = "; ".join(errors)
        finally:
            trace.duration_ms = elapsed()
            trace.ended_at = datetime.now(UTC).isoformat()
            # Weighted DAG path of active compute durations, excluding waiting/cache lookups.
            costs: dict[str, tuple[float, list[str]]] = {}
            for name in graph["order"]:
                s = spans[name]
                base, path = max(
                    (costs[d] for d in s.dependencies), default=(0, []), key=lambda pair: pair[0]
                )
                costs[name] = (base + s.duration_ms, [*path, name])
            if trace.status == "success":
                trace.critical_path_ms, trace.critical_path = max(
                    costs.values(),
                    default=(0, []),
                    key=lambda pair: pair[0],
                )
            if store is not None:
                # TaskGroup is fully drained before persistence, including cancellation.
                await store.save_trace(trace)
        return trace
