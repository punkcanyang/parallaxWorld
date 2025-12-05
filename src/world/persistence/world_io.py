"""Persistence helpers for worlds."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict

from parallax_utils.file_util import get_project_root
from world.core.state import Character, Event, Location, Memory, World


def _dict_to_location(d: Dict) -> Location:
    return Location(
        id=d["id"],
        name=d.get("name", d["id"]),
        kind=d.get("kind", "generic"),
        connections=d.get("connections", []),
        tags=d.get("tags", []),
    )


def _dict_to_character(d: Dict) -> Character:
    return Character(
        id=d["id"],
        name=d.get("name", d["id"]),
        age=d.get("age", 18),
        role=d.get("role", "villager"),
        language=d.get("language", "zh-CN"),
        comprehension=d.get("comprehension", {}),
        attributes=d.get("attributes", {}),
        traits=d.get("traits", {}),
        states=d.get("states", {}),
        relationships=d.get("relationships", {}),
        memory_ids=d.get("memory_ids", []),
        goals=d.get("goals", []),
        flags=d.get("flags", {}),
        location_id=d.get("location_id"),
    )


def _dict_to_memory(d: Dict) -> Memory:
    return Memory(
        id=d["id"],
        owner_id=d["owner_id"],
        summary=d.get("summary", ""),
        salience=d.get("salience", 1.0),
        tags=d.get("tags", []),
        created_at=d.get("created_at", 0),
        decay_rate=d.get("decay_rate", 0.01),
    )


def _dict_to_event(d: Dict) -> Event:
    return Event(
        id=d["id"],
        type=d.get("type", "generic"),
        created_at=d.get("created_at", 0),
        scheduled_for=d.get("scheduled_for", 0),
        location_id=d.get("location_id"),
        actors=d.get("actors", []),
        payload=d.get("payload", {}),
        origin=d.get("origin", "system"),
        status=d.get("status", "scheduled"),
        effects=d.get("effects", []),
    )


def save_world(world: World, base_dir: Path) -> None:
    base_dir = Path(base_dir)
    if not base_dir.is_absolute():
        base_dir = get_project_root() / base_dir
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / "world.json"
    data = asdict(world)
    # logs can be large; don't persist runtime logs in world snapshot
    data.pop("logs", None)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_world(world_id: str, base_dir: Path) -> World:
    base_dir = Path(base_dir)
    if not base_dir.is_absolute():
        base_dir = get_project_root() / base_dir
    world_dir = base_dir / world_id
    world_dir.mkdir(parents=True, exist_ok=True)
    path = world_dir / "world.json"
    if not path.exists():
        # create a default world
        return World(
            id=world_id,
            name=world_id,
            background="A new world",
            default_language="zh-CN",
            force_default_language=True,
            locations={"loc-1": Location(id="loc-1", name="Square", kind="center")},
        )

    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    world = World(
        id=raw.get("id", world_id),
        name=raw.get("name", world_id),
        background=raw.get("background", ""),
        epoch=raw.get("epoch", 0),
        time_scale=raw.get("time_scale", 1.0),
        default_language=raw.get("default_language", "zh-CN"),
        force_default_language=raw.get("force_default_language", True),
        env_state=raw.get("env_state", {}),
    )
    world.locations = {
        loc_id: _dict_to_location(loc) for loc_id, loc in raw.get("locations", {}).items()
    }
    world.characters = {
        cid: _dict_to_character(ch) for cid, ch in raw.get("characters", {}).items()
    }
    world.memories = {
        mid: _dict_to_memory(mem) for mid, mem in raw.get("memories", {}).items()
    }
    world.events = {eid: _dict_to_event(ev) for eid, ev in raw.get("events", {}).items()}
    return world
