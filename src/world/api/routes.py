"""Minimal API for the world simulation."""

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from world.core.manager import MultiWorldManager
from world.core.state import Character, Event, WorldStore
from world.core.time import SimulationClock
from world.fate.engine import FateEngine

router = APIRouter()

_store: Optional[WorldStore] = None
_clock: Optional[SimulationClock] = None
_engine: Optional[FateEngine] = None
_manager: Optional[MultiWorldManager] = None


def configure_world(
    store: WorldStore, clock: SimulationClock, engine: FateEngine, manager: Optional[MultiWorldManager] = None
) -> None:
    """Inject dependencies from the host app."""
    global _store, _clock, _engine, _manager
    _store = store
    _clock = clock
    _engine = engine
    _manager = manager


def _require_store() -> WorldStore:
    if _store is None:
        raise HTTPException(status_code=500, detail="WorldStore not configured")
    return _store


def _require_clock() -> SimulationClock:
    if _clock is None:
        raise HTTPException(status_code=500, detail="SimulationClock not configured")
    return _clock


def _require_engine() -> FateEngine:
    if _engine is None:
        raise HTTPException(status_code=500, detail="FateEngine not configured")
    return _engine


def _require_manager() -> MultiWorldManager:
    if _manager is None:
        raise HTTPException(status_code=500, detail="World manager not configured")
    return _manager


@router.get("/world")
def get_world():
    store = _require_store()
    return asdict(store.world)


@router.post("/world/time-scale")
def set_time_scale(payload: Dict[str, Any]):
    clock = _require_clock()
    scale = float(payload.get("time_scale", 1.0))
    clock.set_time_scale(scale)
    return {"time_scale": clock.config.time_scale}


@router.post("/characters")
def create_character(payload: Dict[str, Any]):
    store = _require_store()
    character = Character(
        id=str(payload["id"]),
        name=payload.get("name", "unknown"),
        age=int(payload.get("age", 18)),
        role=payload.get("role", "villager"),
        language=payload.get("language", store.world.default_language),
        comprehension=payload.get("comprehension", {}),
        attributes=payload.get("attributes", {}),
        traits=payload.get("traits", {}),
        states=payload.get("states", {}),
        relationships={},
        memory_ids=[],
        goals=[],
        flags=payload.get("flags", {}),
        location_id=payload.get("location_id"),
    )
    store.add_character(character)
    store.save()
    return {"created": asdict(character)}

@router.get("/characters")
def list_characters():
    store = _require_store()
    return {"characters": [asdict(c) for c in store.world.characters.values()]}

@router.get("/characters/{char_id}")
def get_character(char_id: str):
    store = _require_store()
    c = store.world.characters.get(char_id)
    if not c:
        raise HTTPException(status_code=404, detail="character not found")
    return asdict(c)


@router.get("/events")
def list_events(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
):
    store = _require_store()
    events = list(store.world.events.values())[-limit:]
    if status:
        events = [ev for ev in events if ev.status == status]
    return {"events": [asdict(ev) for ev in events], "status": status, "limit": limit}


@router.post("/events")
def create_event(payload: Dict[str, Any]):
    store = _require_store()
    event = Event(
        id=str(payload["id"]),
        type=payload.get("type", "generic"),
        created_at=payload.get("created_at", 0),
        scheduled_for=payload.get("scheduled_for", 0),
        location_id=payload.get("location_id"),
        actors=payload.get("actors", []),
        payload=payload.get("payload", {}),
        origin=payload.get("origin", "manual"),
        status=payload.get("status", "scheduled"),
        effects=payload.get("effects", []),
    )
    store.add_event(event)
    return {"created": asdict(event)}


@router.post("/simulate/step")
def simulate_step():
    store = _require_store()
    clock = _require_clock()
    engine = _require_engine()

    def _on_tick(tick: int):
        store.advance_epoch()
        engine.on_tick(tick)
        engine.process_due_events(tick)
        store.save()

    clock.step(_on_tick)
    return {"tick": clock.tick, "epoch": store.world.epoch}


@router.post("/simulate/start")
def simulate_start():
    store = _require_store()
    clock = _require_clock()
    engine = _require_engine()

    def _on_tick(tick: int):
        store.advance_epoch()
        engine.on_tick(tick)
        engine.process_due_events(tick)

    clock.start(_on_tick)
    return {"running": clock.is_running, "tick": clock.tick, "epoch": store.world.epoch}


@router.post("/simulate/stop")
def simulate_stop():
    clock = _require_clock()
    clock.stop()
    return {"running": clock.is_running, "tick": clock.tick}


@router.get("/logs/tail")
def logs_tail(limit: int = 10, kind: str | None = None):
    store = _require_store()
    logs = store.get_logs_tail(limit)
    if kind:
        logs = [l for l in logs if l.get("type") == kind]
    return {"logs": logs, "limit": limit, "kind": kind}


@router.get("/characters/{char_id}/memories")
def get_memories(char_id: str, limit: int = Query(20, ge=1, le=200)):
    store = _require_store()
    c = store.world.characters.get(char_id)
    if not c:
        raise HTTPException(status_code=404, detail="character not found")
    mems = [store.world.memories[mid] for mid in c.memory_ids if mid in store.world.memories]
    mems = mems[-limit:]
    return {"memories": [asdict(m) for m in mems], "limit": limit}


@router.post("/characters/{char_id}/memories/summarize")
def summarize_memories(char_id: str, limit: int = Query(20, ge=1, le=200)):
    store = _require_store()
    mgr = _manager  # optional manager for llm
    if char_id not in store.world.characters:
        raise HTTPException(status_code=404, detail="character not found")
    llm = mgr.llm if mgr else None
    if llm is None:
        raise HTTPException(status_code=500, detail="LLM not configured")
    summary_mem = store.summarize_memories(llm, char_id, limit=limit)
    if summary_mem is None:
        return {"summary": None, "status": "no memories"}
    return {"summary": asdict(summary_mem)}
