"""In-memory world state store."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Location:
    id: str
    name: str
    kind: str = "generic"
    connections: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class Memory:
    id: str
    owner_id: str
    summary: str
    salience: float = 1.0
    tags: List[str] = field(default_factory=list)
    created_at: int = 0
    decay_rate: float = 0.01


@dataclass
class Character:
    id: str
    name: str
    age: int
    role: str
    attributes: Dict[str, float] = field(default_factory=dict)
    traits: Dict[str, float] = field(default_factory=dict)
    states: Dict[str, float] = field(default_factory=dict)
    relationships: Dict[str, float] = field(default_factory=dict)  # target_id -> score
    memory_ids: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    flags: Dict[str, bool] = field(default_factory=dict)
    location_id: Optional[str] = None


@dataclass
class Event:
    id: str
    type: str
    created_at: int
    scheduled_for: int
    location_id: Optional[str]
    actors: List[str] = field(default_factory=list)
    payload: Dict = field(default_factory=dict)
    origin: str = "system"
    status: str = "scheduled"
    effects: List[Dict] = field(default_factory=list)


@dataclass
class World:
    id: str
    name: str
    background: str
    epoch: int = 0
    time_scale: float = 1.0
    env_state: Dict = field(default_factory=dict)
    locations: Dict[str, Location] = field(default_factory=dict)
    characters: Dict[str, Character] = field(default_factory=dict)
    memories: Dict[str, Memory] = field(default_factory=dict)
    events: Dict[str, Event] = field(default_factory=dict)


class WorldStore:
    """Lightweight in-memory store; add persistence later."""

    def __init__(self, world: World):
        self.world = world

    def add_location(self, location: Location) -> None:
        self.world.locations[location.id] = location

    def add_character(self, character: Character) -> None:
        self.world.characters[character.id] = character

    def add_memory(self, memory: Memory) -> None:
        self.world.memories[memory.id] = memory
        if memory.owner_id in self.world.characters:
            self.world.characters[memory.owner_id].memory_ids.append(memory.id)

    def add_event(self, event: Event) -> None:
        self.world.events[event.id] = event

    def advance_epoch(self) -> int:
        self.world.epoch += 1
        return self.world.epoch

