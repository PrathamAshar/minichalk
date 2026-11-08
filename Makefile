.PHONY: install dev test check benchmark types
install:
	uv sync --project backend --frozen
	npm ci --prefix frontend

dev:
	python3 scripts/dev.py

test:
	cd backend && uv run pytest -q

check:
	cd backend && uv run ruff check .
	npm --prefix frontend run typecheck
	npm --prefix frontend run lint
	npm --prefix frontend run build

benchmark:
	cd backend && uv run python ../benchmarks/run.py --iterations 20

types:
	cd backend && uv run python ../scripts/export_openapi.py
	npm --prefix frontend run generate:api
