"""NDJSON log helpers for world simulation."""

import json
import os
from collections import deque
from pathlib import Path
from typing import Dict, List

LOG_DIR = Path("data/world")
LOG_PATH = LOG_DIR / "event.log"


def append_ndjson(entry: Dict) -> None:
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # best-effort; swallow to avoid breaking simulation loop
        pass


def tail_ndjson(limit: int = 10) -> List[Dict]:
    if not LOG_PATH.exists() or limit <= 0:
        return []
    buf: deque = deque(maxlen=limit)
    try:
        with LOG_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    buf.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []
    return list(buf)

