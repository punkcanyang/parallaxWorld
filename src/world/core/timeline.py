"""Timeline model to orchestrate scenes."""

from dataclasses import dataclass, field
from typing import List
import uuid


def new_timeline_id() -> str:
    return str(uuid.uuid4())


@dataclass
class Timeline:
    id: str
    title: str
    scenes: List[str] = field(default_factory=list)  # list of scene ids
    current_scene_idx: int = 0
    status: str = "active"  # active/completed
    participants: List[str] = field(default_factory=list)
    background_tags: List[str] = field(default_factory=list)
    max_scenes: int = 3
