"""Bounded TTL cache. Generation fencing prevents late writes after invalidation."""

import asyncio
import copy
import time
from collections import OrderedDict
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

Key = tuple[str, str, str, str]


class Cache:
    def __init__(self, max_entries: int = 4096, clock: Callable[[], float] = time.monotonic):
        self.entries: OrderedDict[Key, tuple[float, Any]] = OrderedDict()
        self.locks: dict[Key, tuple[asyncio.Lock, int]] = {}
        self.generation = 0
        self.max_entries = max_entries
        self.clock = clock

    def get(self, key: Key) -> tuple[bool, Any]:
        entry = self.entries.get(key)
        if entry is None:
            return False, None
        if entry[0] <= self.clock():
            del self.entries[key]
            return False, None
        self.entries.move_to_end(key)
        return True, copy.deepcopy(entry[1])

    def put(self, key: Key, value: Any, ttl: float, generation: int) -> None:
        if ttl <= 0 or generation != self.generation:
            return
        self.entries[key] = (self.clock() + ttl, copy.deepcopy(value))
        self.entries.move_to_end(key)
        while len(self.entries) > self.max_entries:
            self.entries.popitem(last=False)

    @asynccontextmanager
    async def singleflight(self, key: Key) -> AsyncIterator[None]:
        lock, count = self.locks.get(key, (asyncio.Lock(), 0))
        self.locks[key] = (lock, count + 1)
        try:
            async with lock:
                yield
        finally:
            _, count = self.locks[key]
            if count == 1:
                del self.locks[key]
            else:
                self.locks[key] = (lock, count - 1)

    def invalidate(self, features: set[str], entity_id: str | None = None) -> int:
        self.generation += 1
        keys = [
            k for k in self.entries if k[0] in features and (entity_id is None or k[1] == entity_id)
        ]
        for key in keys:
            del self.entries[key]
        return len(keys)
