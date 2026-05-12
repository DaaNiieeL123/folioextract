from backend.server import app
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
out_file = root / "docs" / "openapi.json"
out_file.parent.mkdir(parents=True, exist_ok=True)

with open(out_file, "w", encoding="utf-8") as f:
    json.dump(app.openapi(), f)
