"""Manage multiple worlds and persistence."""

from pathlib import Path

from parallax_utils.file_util import get_project_root
from world.core.state import WorldStore
from world.core.time import SimulationClock
from world.fate.engine import FateEngine, build_default_rules
from world.llm.client import HttpLLMClient
from world.logs.io import set_log_dir
from world.persistence.world_io import load_world, save_world


class MultiWorldManager:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or (get_project_root() / "data/worlds")
        self.current_world_id = "default"
        self.clock = SimulationClock()
        self.llm = HttpLLMClient()
        self.store = self._load_world(self.current_world_id)
        self.engine = FateEngine(self.store, self.llm)
        self.engine.register_many(build_default_rules(self.store))

    def _world_dir(self, world_id: str) -> Path:
        return self.base_dir / world_id

    def _load_world(self, world_id: str) -> WorldStore:
        world = load_world(world_id, self.base_dir)
        set_log_dir(self._world_dir(world_id))
        store = WorldStore(world, storage_dir=self._world_dir(world_id))
        save_world(store.world, self._world_dir(world_id))
        return store

    def list_worlds(self):
        if not self.base_dir.exists():
            return []
        return [p.name for p in self.base_dir.iterdir() if p.is_dir()]

    def create_world(self, world_id: str, name: str, background: str, default_language: str, force_default_language: bool):
        world_dir = self._world_dir(world_id)
        world_dir.mkdir(parents=True, exist_ok=True)
        from world.core.state import Location, World

        world = World(
            id=world_id,
            name=name or world_id,
            background=background,
            default_language=default_language,
            force_default_language=force_default_language,
            locations={"loc-1": Location(id="loc-1", name="Square", kind="center")},
        )
        save_world(world, world_dir)
        return world_id

    def select_world(self, world_id: str):
        self.current_world_id = world_id
        self.clock = SimulationClock()
        self.store = self._load_world(world_id)
        self.engine = FateEngine(self.store, self.llm)
        self.engine.register_many(build_default_rules(self.store))
        return {
            "world_id": world_id,
            "name": self.store.world.name,
            "background": self.store.world.background,
        }
