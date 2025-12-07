"""Load/save map.json for worlds."""

import json
from pathlib import Path
from typing import Dict, List

from parallax_utils.file_util import get_project_root


def _resolve_path(world_id: str, base_dir: Path | None = None) -> Path:
    root = get_project_root()
    base = base_dir or (root / "data" / "worlds")
    base = Path(base)
    if not base.is_absolute():
        base = root / base
    return base / world_id / "map.json"


def load_map(world_id: str, base_dir: Path | None = None) -> Dict:
    path = _resolve_path(world_id, base_dir)
    if not path.exists():
        return {"locations": [], "zones": []}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"locations": [], "zones": []}


def save_map(world_id: str, data: Dict, base_dir: Path | None = None) -> None:
    path = _resolve_path(world_id, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
