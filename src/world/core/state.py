"""In-memory world state store."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from world.logs.io import append_ndjson, tail_ndjson

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
    language: str = "zh-CN"  # preferred output language
    comprehension: Dict[str, float] = field(default_factory=dict)  # language -> confidence 0-1
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
    default_language: str = "zh-CN"
    force_default_language: bool = True  # if True, final output should be in default_language
    env_state: Dict = field(default_factory=dict)
    locations: Dict[str, Location] = field(default_factory=dict)
    characters: Dict[str, Character] = field(default_factory=dict)
    memories: Dict[str, Memory] = field(default_factory=dict)
    events: Dict[str, Event] = field(default_factory=dict)
    logs: list = field(default_factory=list)


class WorldStore:
    """Lightweight in-memory store; add persistence later."""

    def __init__(self, world: World, storage_dir=None):
        self.world = world
        self.logs: list = []
        self.storage_dir = storage_dir
        self.memory_limit = 100  # per character
        self.memory_summary_every_n = 5
        self.memory_summary_max_items = 5
        self.memory_event_count: Dict[str, int] = {}

    def add_location(self, location: Location) -> None:
        self.world.locations[location.id] = location

    def add_character(self, character: Character) -> None:
        self.world.characters[character.id] = character

    def add_memory(self, memory: Memory) -> None:
        self.world.memories[memory.id] = memory
        if memory.owner_id in self.world.characters:
            self.world.characters[memory.owner_id].memory_ids.append(memory.id)
            self.memory_event_count[memory.owner_id] = self.memory_event_count.get(memory.owner_id, 0) + 1
            # enforce memory limit
            ids = self.world.characters[memory.owner_id].memory_ids
            if len(ids) > self.memory_limit:
                # drop oldest from list and dict
                drop = ids[: len(ids) - self.memory_limit]
                self.world.characters[memory.owner_id].memory_ids = ids[-self.memory_limit :]
                for mid in drop:
                    self.world.memories.pop(mid, None)

    def add_event(self, event: Event) -> None:
        self.world.events[event.id] = event

    def advance_epoch(self) -> int:
        self.world.epoch += 1
        return self.world.epoch

    def append_log(self, entry) -> None:
        self.logs.append(entry)
        self.world.logs = self.logs
        append_ndjson(entry)

    def get_logs_tail(self, limit: int = 10):
        if limit <= 0:
            return []
        # prefer on-disk tail to include events from previous runs
        persisted = tail_ndjson(limit)
        if persisted:
            return persisted
        return self.logs[-limit:]

    def save(self):
        if self.storage_dir:
            from world.persistence.world_io import save_world  # local import to avoid cycle
            save_world(self.world, self.storage_dir)

    def summarize_memories(self, llm, char_id: str, limit: int = 20):
        """Summarize recent memories for a character and store a summary memory."""
        if char_id not in self.world.characters:
            return None
        mem_ids = self.world.characters[char_id].memory_ids[-limit:]
        mems = [self.world.memories[mid] for mid in mem_ids if mid in self.world.memories]
        if not mems:
            return None
        mem_payload = [{"summary": m.summary, "tags": m.tags} for m in mems]
        summary_text = llm.summarize_memories(
            mem_payload, max_items=min(limit, self.memory_summary_max_items)
        )
        mem_id = str(uuid.uuid4())
        summary_memory = Memory(
            id=mem_id,
            owner_id=char_id,
            summary=summary_text,
            salience=0.5,
            tags=["summary"],
            created_at=self.world.epoch,
        )
        self.add_memory(summary_memory)
        self.memory_event_count[char_id] = 0
        return summary_memory
