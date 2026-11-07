# scripts/export_openapi.py：把 FastAPI 的 openapi 落到 docs/openapi.json（契约快照）
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mock.app import app  # noqa: E402

target = ROOT / "docs" / "openapi.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
print(f"WROTE {target.relative_to(ROOT)} paths={len(app.openapi()['paths'])}")
