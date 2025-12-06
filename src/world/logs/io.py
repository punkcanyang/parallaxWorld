"""NDJSON log helpers for world simulation."""

import json
import os
import re
import time
from collections import deque
from pathlib import Path
from typing import Dict, List

from parallax_utils.file_util import get_project_root

PROJECT_ROOT = get_project_root()
LOG_DIR = PROJECT_ROOT / "data/worlds/default"
LOG_EVENT_JSON = LOG_DIR / "event.json"
LOG_EVENT_TXT = LOG_DIR / "event.log"
LOG_INCIDENT_JSON = LOG_DIR / "incident.json"


def set_log_dir(world_dir: Path) -> None:
    """Set log directory for the current world."""
    global LOG_DIR, LOG_EVENT_JSON, LOG_EVENT_TXT, LOG_INCIDENT_JSON
    LOG_DIR = PROJECT_ROOT / world_dir
    LOG_EVENT_JSON = LOG_DIR / "event.json"
    LOG_EVENT_TXT = LOG_DIR / "event.log"
    LOG_INCIDENT_JSON = LOG_DIR / "incident.json"


def _strip_think(text: str) -> str:
    """Remove <think>...</think> blocks and trim whitespace."""
    if not isinstance(text, str):
        return text
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip()


def _sanitize_entry(entry: Dict) -> Dict:
    """Produce a human log entry without think/meta, with timestamp."""
    data = dict(entry)
    data["ts"] = time.time()
    if "dialogue" in data:
        data["dialogue"] = _strip_think(data["dialogue"])
    if isinstance(data.get("incident"), dict):
        inc = dict(data["incident"])
        if "description" in inc:
            inc["description"] = _strip_think(inc["description"])
        data["incident"] = inc
    return data


def _format_text_entry(entry: Dict) -> str:
    """Render a compact text log line (no JSON)."""
    parts = []
    ts = entry.get("ts") or time.time()
    tick = entry.get("tick", "-")
    etype = entry.get("type", "event")
    parts.append(f"[{ts:.0f}] tick={tick} type={etype}")
    inc = entry.get("incident") or {}
    if isinstance(inc, dict):
        title = inc.get("title")
        desc = inc.get("description")
        if title:
            parts.append(f"incident={title}")
        if desc:
            parts.append(f"desc={desc}")
    dialogue = entry.get("dialogue")
    if dialogue:
        parts.append(f"dialogue={dialogue}")
    return " | ".join(parts)


def append_ndjson(entry: Dict) -> None:
    """Write full entry to event.json, sanitized text to event.log, and incidents to incident.json."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with LOG_EVENT_JSON.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        sanitized = _sanitize_entry(entry)
        with LOG_EVENT_TXT.open("a", encoding="utf-8") as f:
            f.write(_format_text_entry(sanitized) + "\n")
        if "incident" in entry and entry["incident"]:
            with LOG_INCIDENT_JSON.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry["incident"], ensure_ascii=False) + "\n")
    except Exception:
        # best-effort; swallow to avoid breaking simulation loop
        pass


def tail_ndjson(limit: int = 10) -> List[Dict]:
    """Read tail from event.json (sanitized) for API responses."""
    if not LOG_EVENT_JSON.exists() or limit <= 0:
        return []
    buf: deque = deque(maxlen=limit)
    try:
        with LOG_EVENT_JSON.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                    buf.append(_sanitize_entry(raw))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []
    return list(buf)
