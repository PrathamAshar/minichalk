from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import Graph


class Span(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)
    name: str
    dependencies: list[str]
    status: Literal["waiting", "running", "success", "failed", "cancelled", "skipped"] = "waiting"
    cache: Literal["hit", "miss", "coalesced", "bypass", "unchecked"] = "unchecked"
    start_ms: float | None = None
    end_ms: float | None = None
    duration_ms: float = 0
    error: str | None = None


class Trace(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)
    query_id: str
    entity_id: str
    requested: list[str]
    parameters: dict[str, Any]
    started_at: str
    ended_at: str | None = None
    duration_ms: float = 0
    status: Literal["running", "success", "failed", "timeout", "cancelled"] = "running"
    error: str | None = None
    results: dict[str, Any] = Field(default_factory=dict)
    graph: Graph
    spans: list[Span]
    critical_path: list[str] = Field(default_factory=list)
    critical_path_ms: float = 0
