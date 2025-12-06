"""Scene/conversation model for multi-agent dialogue."""

from dataclasses import dataclass, field
from typing import List, Dict
import time
import uuid


@dataclass
class SceneTurn:
    speaker: str
    utterance: str
    ts: float = field(default_factory=time.time)


@dataclass
class Scene:
    id: str
    title: str
    participants: List[str]
    location_id: str | None = None
    background_tags: List[str] = field(default_factory=list)
    max_turns: int = 6
    turns: List[SceneTurn] = field(default_factory=list)
    status: str = "active"  # active/completed

    def next_speaker(self) -> str:
        idx = len(self.turns) % len(self.participants)
        return self.participants[idx]

    def add_turn(self, speaker: str, utterance: str):
        self.turns.append(SceneTurn(speaker=speaker, utterance=utterance))
        if len(self.turns) >= self.max_turns:
            self.status = "completed"


def new_scene_id() -> str:
    return str(uuid.uuid4())
