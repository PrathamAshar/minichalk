import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from app.engine.executor import Executor
from app.engine.tracing import Trace
from app.features.fraud import build_registry
from app.models import (
    Entity,
    FeatureMetadata,
    Graph,
    Health,
    InvalidateRequest,
    Invalidation,
    QueryRequest,
    Stats,
)
from app.sources.database import Database
from app.sources.demo import DemoSources


def create_app(database_path: str | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database = Database(database_path or os.getenv("MINICHALK_DB", "data/minichalk.sqlite3"))
        await database.open()
        app.state.database = database
        app.state.registry = build_registry()
        app.state.executor = Executor(app.state.registry, sources=DemoSources(database))
        try:
            yield
        finally:
            await database.close()

    app = FastAPI(
        title="MiniChalk",
        version="0.1.0",
        lifespan=lifespan,
        description="Independent educational feature engine. No affiliation with Chalk.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(ValueError)
    async def invalid_request(request: Request, exc: ValueError):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.get("/api/health", response_model=Health)
    async def health():
        return {
            "status": "ok",
            "as_of": (await app.state.database.as_of()).isoformat(),
            "artificial_io_delay_ms": 120,
        }

    @app.get("/api/entities", response_model=list[Entity])
    async def entities():
        return await app.state.database.rows("SELECT * FROM users ORDER BY id")

    @app.get("/api/features", response_model=list[FeatureMetadata])
    async def features():
        return [f.metadata() for _, f in sorted(app.state.registry.features.items())]

    @app.get("/api/features/{feature_name}", response_model=FeatureMetadata)
    async def feature(feature_name: str):
        f = app.state.registry.features.get(feature_name)
        if f is None:
            raise HTTPException(404, "Feature not found")
        return f.metadata()

    @app.get("/api/features/{feature_name}/graph", response_model=Graph)
    async def feature_graph(feature_name: str):
        return app.state.registry.plan([feature_name])

    @app.post("/api/plan", response_model=Graph)
    async def plan(body: QueryRequest):
        return app.state.registry.plan(body.features)

    @app.post("/api/query", response_model=Trace)
    async def query(body: QueryRequest):
        users = await app.state.database.rows("SELECT id FROM users WHERE id=?", (body.entity_id,))
        if not users:
            raise HTTPException(404, "Entity not found")
        return await app.state.executor.query(
            body.entity_id,
            body.features,
            body.parameters,
            body.bypass_cache,
            body.timeout_seconds,
            store=app.state.database,
        )

    @app.get("/api/traces", response_model=list[Trace])
    async def traces(limit: int = Query(100, ge=1, le=1000)):
        return await app.state.database.traces(limit)

    @app.get("/api/traces/{query_id}", response_model=Trace)
    async def trace(query_id: str):
        result = await app.state.database.trace(query_id)
        if result is None:
            raise HTTPException(404, "Trace not found")
        return result

    @app.get("/api/stats", response_model=Stats)
    async def stats():
        return {
            **await app.state.database.stats(),
            "registered_features": len(app.state.registry.features),
        }

    @app.post("/api/cache/invalidate", response_model=Invalidation)
    async def invalidate(body: InvalidateRequest):
        affected = app.state.registry.affected(body.feature)
        removed = app.state.executor.cache.invalidate(affected, body.entity_id)
        return {"removed": removed, "affected_features": sorted(affected)}

    return app


app = create_app()
