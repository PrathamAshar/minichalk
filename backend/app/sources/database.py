"""All SQLite work runs through aiosqlite's worker thread."""

import asyncio
import math
import random
import statistics
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

from app.engine.tracing import Trace


class Database:
    def __init__(self, path: str):
        self.path = path
        self.connection: aiosqlite.Connection | None = None
        self.write_lock = asyncio.Lock()

    @property
    def db(self) -> aiosqlite.Connection:
        assert self.connection is not None, "Database has not been opened"
        return self.connection

    async def open(self) -> None:
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = await aiosqlite.connect(self.path)
        self.db.row_factory = aiosqlite.Row
        await self.db.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, name TEXT, profile TEXT);
        CREATE TABLE IF NOT EXISTS merchants(id TEXT PRIMARY KEY, name TEXT, risk REAL);
        CREATE TABLE IF NOT EXISTS devices(id TEXT PRIMARY KEY, risk REAL);
        CREATE TABLE IF NOT EXISTS transactions(
            id INTEGER PRIMARY KEY, user_id TEXT REFERENCES users(id), amount REAL,
            merchant_id TEXT REFERENCES merchants(id), occurred_at TEXT);
        CREATE INDEX IF NOT EXISTS tx_user_time ON transactions(user_id, occurred_at);
        CREATE TABLE IF NOT EXISTS device_sessions(
            id INTEGER PRIMARY KEY, user_id TEXT REFERENCES users(id),
            device_id TEXT REFERENCES devices(id), occurred_at TEXT);
        CREATE INDEX IF NOT EXISTS session_user_time ON device_sessions(user_id, occurred_at);
        CREATE TABLE IF NOT EXISTS traces(id TEXT PRIMARY KEY, started_at TEXT, body TEXT);
        CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT);
        """)
        users = await self.rows("SELECT * FROM users")
        if not users:
            await self.seed()

    async def close(self) -> None:
        if self.connection:
            await self.connection.close()

    async def rows(self, sql: str, args: tuple = ()) -> list[dict[str, Any]]:
        async with self.db.execute(sql, args) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def seed(self) -> None:
        # Stable random seed and persisted reference time make fixtures reproducible.
        rng = random.Random(42)
        anchor = datetime.now(UTC).replace(microsecond=0)
        await self.db.execute("INSERT INTO metadata VALUES ('as_of', ?)", (anchor.isoformat(),))
        await self.db.executemany(
            "INSERT INTO users VALUES (?, ?, ?)",
            [
                ("usr_ada", "Ada Chen", "normal"),
                ("usr_milo", "Milo Rivera", "elevated"),
                ("usr_nova", "Nova Patel", "suspicious"),
            ],
        )
        await self.db.executemany(
            "INSERT INTO merchants VALUES (?, ?, ?)",
            [
                ("m_cafe", "Corner Coffee", 0.03),
                ("m_market", "Daily Market", 0.08),
                ("m_crypto", "Offshore Exchange", 0.92),
            ],
        )
        await self.db.executemany(
            "INSERT INTO devices VALUES (?, ?)", [(f"dev_{i}", round(i / 10, 2)) for i in range(10)]
        )
        for uid, count, recent, devices in [
            ("usr_ada", 18, 1, 1),
            ("usr_milo", 35, 5, 3),
            ("usr_nova", 65, 24, 8),
        ]:
            for i in range(count):
                age = rng.uniform(0, 9) if i < recent else rng.uniform(11, 1400)
                amount = rng.uniform(8, 120) if uid == "usr_ada" else rng.uniform(100, 1600)
                merchant = "m_crypto" if uid == "usr_nova" and i % 2 else "m_market"
                await self.db.execute(
                    "INSERT INTO transactions(user_id,amount,merchant_id,occurred_at) "
                    "VALUES(?,?,?,?)",
                    (
                        uid,
                        round(amount, 2),
                        merchant,
                        (anchor - timedelta(minutes=age)).isoformat(),
                    ),
                )
            for i in range(devices):
                await self.db.execute(
                    "INSERT INTO device_sessions(user_id,device_id,occurred_at) VALUES(?,?,?)",
                    (uid, f"dev_{i}", (anchor - timedelta(hours=i)).isoformat()),
                )
        await self.db.commit()

    async def as_of(self) -> datetime:
        row = (await self.rows("SELECT value FROM metadata WHERE key='as_of'"))[0]
        return datetime.fromisoformat(row["value"])

    async def save_trace(self, trace: Trace) -> None:
        async with self.write_lock:
            await self.db.execute(
                "INSERT OR REPLACE INTO traces VALUES (?, ?, ?)",
                (trace.query_id, trace.started_at, trace.model_dump_json()),
            )
            await self.db.execute("""DELETE FROM traces WHERE id NOT IN
                (SELECT id FROM traces ORDER BY started_at DESC LIMIT 1000)""")
            await self.db.commit()

    async def traces(self, limit: int = 100) -> list[Trace]:
        return [
            Trace.model_validate_json(r["body"])
            for r in await self.rows(
                "SELECT body FROM traces ORDER BY started_at DESC LIMIT ?",
                (limit,),
            )
        ]

    async def trace(self, query_id: str) -> Trace | None:
        rows = await self.rows("SELECT body FROM traces WHERE id=?", (query_id,))
        return Trace.model_validate_json(rows[0]["body"]) if rows else None

    async def stats(self) -> dict[str, Any]:
        traces = await self.traces(1000)
        durations = sorted(t.duration_ms for t in traces)
        spans = [s for t in traces for s in t.spans]
        hits = sum(s.cache in ("hit", "coalesced") for s in spans)
        lookups = sum(s.cache in ("hit", "coalesced", "miss") for s in spans)
        return {
            "query_count": len(traces),
            "successful_queries": sum(t.status == "success" for t in traces),
            "median_ms": statistics.median(durations) if durations else None,
            "p95_ms": durations[max(0, math.ceil(len(durations) * 0.95) - 1)]
            if durations
            else None,
            "cache_hit_rate": hits / lookups if lookups else None,
            "cache_lookups": lookups,
            "window": "most recent 1000 persisted queries",
        }
