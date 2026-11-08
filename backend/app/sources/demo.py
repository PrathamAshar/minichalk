import asyncio
from datetime import timedelta
from typing import Any

from app.sources.database import Database


class DemoSources:
    def __init__(self, database: Database, external_delay: float = 0.12):
        self.database = database
        self.external_delay = external_delay

    async def cutoff(self, minutes: int) -> str:
        return ((await self.database.as_of()) - timedelta(minutes=minutes)).isoformat()

    async def transactions(
        self, entity_id: str, minutes: int | None = None
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM transactions WHERE user_id=?"
        args = (entity_id,)
        if minutes is not None:
            query += " AND occurred_at>=?"
            args = (entity_id, await self.cutoff(minutes))
        return await self.database.rows(query, args)

    async def device_rows(self, entity_id: str) -> list[dict[str, Any]]:
        return await self.database.rows(
            """SELECT DISTINCT d.id,d.risk FROM devices d
            JOIN device_sessions s ON s.device_id=d.id WHERE s.user_id=? AND s.occurred_at>=?""",
            (entity_id, await self.cutoff(7 * 24 * 60)),
        )

    async def merchant_risk(self, entity_id: str) -> float:
        # Intentionally artificial external I/O delay; no remote service is called.
        await asyncio.sleep(self.external_delay)
        rows = await self.database.rows(
            """SELECT MAX(m.risk) AS risk FROM merchants m
            JOIN transactions t ON t.merchant_id=m.id WHERE t.user_id=? AND t.occurred_at>=?""",
            (entity_id, await self.cutoff(24 * 60)),
        )
        return float(rows[0]["risk"] or 0)
