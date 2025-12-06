"""Story/scene log helpers."""

import os
import time
from pathlib import Path

from parallax_utils.file_util import get_project_root

PROJECT_ROOT = get_project_root()


def get_story_paths(world_dir: Path):
    base = PROJECT_ROOT / world_dir
    return {
        "json": base / "story.json",
        "txt": base / "story.log",
    }


def append_story(world_dir: Path, scene_id: str, turn: dict):
    paths = get_story_paths(world_dir)
    os.makedirs(paths["json"].parent, exist_ok=True)
    turn = dict(turn)
    turn["ts"] = turn.get("ts") or time.time()
    turn["scene_id"] = scene_id
    # json line
    try:
        import json

        with paths["json"].open("a", encoding="utf-8") as f:
            f.write(json.dumps(turn, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # text line
    try:
        speaker = turn.get("speaker", "")
        utter = turn.get("utterance", "")
        with paths["txt"].open("a", encoding="utf-8") as f:
            f.write(f"[{turn['ts']:.0f}] scene={scene_id} speaker={speaker} | {utter}\n")
    except Exception:
        pass
