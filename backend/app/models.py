from typing import Any

from pydantic import BaseModel, Field, JsonValue


class QueryRequest(BaseModel):
    entity_id: str = Field(min_length=1, max_length=128)
    features: list[str] = Field(min_length=1, max_length=50)
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    bypass_cache: bool = False
    timeout_seconds: float = Field(default=5, gt=0, le=30, allow_inf_nan=False)


class InvalidateRequest(BaseModel):
    feature: str | None = None
    entity_id: str | None = None


class FeatureMetadata(BaseModel):
    name: str
    dependencies: list[str]
    ttl_seconds: float
    version: str
    description: str
    output_type: dict[str, Any]


class Node(BaseModel):
    id: str
    level: int
    requested: bool


class Edge(BaseModel):
    source: str
    target: str


class Graph(BaseModel):
    requested: list[str]
    order: list[str]
    nodes: list[Node]
    edges: list[Edge]
    layers: list[list[str]]


class Entity(BaseModel):
    id: str
    name: str
    profile: str


class Stats(BaseModel):
    registered_features: int
    query_count: int
    successful_queries: int
    median_ms: float | None
    p95_ms: float | None
    cache_hit_rate: float | None
    cache_lookups: int
    window: str


class Invalidation(BaseModel):
    removed: int
    affected_features: list[str]


class Health(BaseModel):
    status: str
    as_of: str
    artificial_io_delay_ms: float
