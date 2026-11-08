from typing import Any

from app.engine.executor import Context
from app.engine.registry import Registry


def build_registry() -> Registry:
    r = Registry()

    @r.feature("user.transaction_count_10m", ttl_seconds=30)
    async def count_10m(ctx: Context) -> int:
        """Transactions in the ten minutes before the persisted demo reference time."""
        return len(await ctx.sources.transactions(ctx.entity_id, 10))

    @r.feature("user.transaction_count_24h", ttl_seconds=60)
    async def count_24h(ctx: Context) -> int:
        """Transactions in the 24-hour demo window."""
        return len(await ctx.sources.transactions(ctx.entity_id, 1440))

    @r.feature("user.average_transaction_amount", ttl_seconds=60)
    async def average(ctx: Context) -> float:
        """Mean amount across the user's complete seeded transaction history, in USD."""
        rows = await ctx.sources.transactions(ctx.entity_id)
        return round(sum(t["amount"] for t in rows) / len(rows), 2) if rows else 0.0

    @r.feature("user.total_spend_24h", ttl_seconds=60)
    async def total(ctx: Context) -> float:
        """Total USD spend within the 24-hour demo window."""
        return round(
            sum(t["amount"] for t in await ctx.sources.transactions(ctx.entity_id, 1440)), 2
        )

    @r.feature("user.unique_devices_7d", ttl_seconds=120)
    async def unique_devices(ctx: Context) -> int:
        """Number of distinct devices observed within seven days."""
        return len(await ctx.sources.device_rows(ctx.entity_id))

    @r.feature("user.device_risk", dependencies=["user.unique_devices_7d"], ttl_seconds=30)
    async def device_risk(ctx: Context, deps: dict[str, Any]) -> float:
        """Artificial 120ms external I/O, then max device risk plus device-count penalty."""
        import asyncio

        await asyncio.sleep(ctx.sources.external_delay)
        rows = await ctx.sources.device_rows(ctx.entity_id)
        baseline = max((d["risk"] for d in rows), default=0)
        return round(min(1.0, baseline + max(0, deps["user.unique_devices_7d"] - 2) * 0.04), 4)

    @r.feature("user.merchant_risk", ttl_seconds=60)
    async def merchant_risk(ctx: Context) -> float:
        """Highest recent merchant risk. Artificial 120ms external I/O; no network call."""
        return await ctx.sources.merchant_risk(ctx.entity_id)

    @r.feature(
        "user.transaction_velocity",
        dependencies=["user.transaction_count_10m", "user.transaction_count_24h"],
        ttl_seconds=30,
    )
    async def velocity(ctx: Context, deps: dict[str, Any]) -> float:
        """Recent count / max(1, 24-hour count / 144), capped at 20."""
        return round(
            min(
                20.0,
                deps["user.transaction_count_10m"]
                / max(1.0, deps["user.transaction_count_24h"] / 144),
            ),
            4,
        )

    @r.feature(
        "user.fraud_score",
        dependencies=[
            "user.transaction_velocity",
            "user.average_transaction_amount",
            "user.total_spend_24h",
            "user.device_risk",
            "user.merchant_risk",
        ],
        ttl_seconds=15,
    )
    async def score(ctx: Context, deps: dict[str, Any]) -> float:
        """0–100 demo risk: 30% velocity, 25% device, 20% merchant, 15% spend, 10% amount."""
        return round(
            100
            * (
                0.30 * min(1.0, deps["user.transaction_velocity"] / 10)
                + 0.25 * deps["user.device_risk"]
                + 0.20 * deps["user.merchant_risk"]
                + 0.15 * min(1.0, deps["user.total_spend_24h"] / 20000)
                + 0.10 * min(1.0, deps["user.average_transaction_amount"] / 1000)
            ),
            2,
        )

    r.validate()
    return r
