from typing import Any
from pathlib import Path
import json

def load_json_schema(path: str) -> dict[str, Any]:
    p = Path(path)
    return json.loads(p.read_text(encoding='utf-8'))