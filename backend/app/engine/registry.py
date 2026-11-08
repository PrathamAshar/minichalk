"""Executable definitions and deterministic graph validation; no dynamic evaluation."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, get_type_hints

from pydantic import TypeAdapter


@dataclass(frozen=True)
class Feature:
    name: str
    dependencies: tuple[str, ...]
    ttl_seconds: float
    version: str
    description: str
    fn: Callable[..., Awaitable[Any]]
    adapter: TypeAdapter[Any]

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "dependencies": list(self.dependencies),
            "ttl_seconds": self.ttl_seconds,
            "version": self.version,
            "description": self.description,
            "output_type": self.adapter.json_schema(),
        }


class Registry:
    def __init__(self) -> None:
        self.features: dict[str, Feature] = {}

    def feature(
        self,
        name: str,
        dependencies: list[str] | None = None,
        ttl_seconds: float = 0,
        version: str = "1",
    ) -> Callable:
        def register(fn: Callable[..., Awaitable[Any]]) -> Callable:
            if name in self.features:
                raise ValueError(f"Duplicate feature: {name}")
            if ttl_seconds < 0:
                raise ValueError("TTL must be nonnegative")
            import inspect

            if not inspect.iscoroutinefunction(fn):
                raise ValueError(f"Feature {name} must be an async function")
            annotation = get_type_hints(fn).get("return", Any)
            self.features[name] = Feature(
                name,
                tuple(sorted(set(dependencies or []))),
                ttl_seconds,
                version,
                inspect.getdoc(fn) or "",
                fn,
                TypeAdapter(annotation),
            )
            return fn

        return register

    def plan(self, requested: list[str]) -> dict[str, Any]:
        if not requested:
            raise ValueError("Request at least one feature")
        ordered: list[str] = []
        visiting: list[str] = []
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visiting:
                raise ValueError("Dependency cycle: " + " -> ".join([*visiting, name]))
            if name in visited:
                return
            if name not in self.features:
                raise ValueError(f"Missing feature: {name} (required by {visiting[-1:]})")
            visiting.append(name)
            for dep in self.features[name].dependencies:
                visit(dep)
            visiting.pop()
            visited.add(name)
            ordered.append(name)

        for name in sorted(set(requested)):
            visit(name)
        levels: dict[str, int] = {}
        for name in ordered:
            levels[name] = 1 + max(
                (levels[d] for d in self.features[name].dependencies),
                default=-1,
            )
        return {
            "requested": sorted(set(requested)),
            "order": ordered,
            "nodes": [{"id": n, "level": levels[n], "requested": n in requested} for n in ordered],
            "edges": [
                {"source": d, "target": n} for n in ordered for d in self.features[n].dependencies
            ],
            "layers": [
                [n for n in ordered if levels[n] == i] for i in range(max(levels.values()) + 1)
            ],
        }

    def validate(self) -> None:
        if self.features:
            self.plan(list(self.features))

    def affected(self, feature: str | None) -> set[str]:
        if feature is None:
            return set(self.features)
        if feature not in self.features:
            raise ValueError(f"Unknown feature: {feature}")
        affected = {feature}
        while True:
            expanded = affected | {
                n for n, f in self.features.items() if affected.intersection(f.dependencies)
            }
            if expanded == affected:
                return affected
            affected = expanded
