"""Run from backend: uv run python ../scripts/export_openapi.py"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.main import app  # noqa: E402

(ROOT / "backend" / "openapi.json").write_text(json.dumps(app.openapi(), indent=2) + "\n")
