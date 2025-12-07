"""Minimal API for the world simulation."""

import random
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query

from world.core.manager import MultiWorldManager
from world.core.state import Character, Event, WorldStore
from world.core.time import SimulationClock
from world.fate.engine import FateEngine
from world.core.scene import Scene, new_scene_id
from world.core.timeline import Timeline, new_timeline_id
from world.logs.story_io import append_story
from world.persistence.map_io import load_map, save_map

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


def _select_participants(store: WorldStore, provided: List[str] | None, max_count: int = 3, location_id: Optional[str] = None) -> List[str]:
    actor_ids = provided or list(store.world.characters.keys())
    if not actor_ids:
        return []
    if location_id and store.world.locations.get(location_id) and store.world.locations[location_id].coords:
        target = store.world.locations[location_id].coords

        def dist_to(actor_id: str) -> float:
            ch = store.world.characters.get(actor_id)
            if not ch:
                return 1e9
            loc_id = ch.location_id
            if loc_id and store.world.locations.get(loc_id) and store.world.locations[loc_id].coords:
                loc = store.world.locations[loc_id].coords
                dx = loc.get("x", 0) - target.get("x", 0)
                dy = loc.get("y", 0) - target.get("y", 0)
                return (dx * dx + dy * dy) ** 0.5
            return 1e9

        actor_ids = sorted(actor_ids, key=dist_to)
    if len(actor_ids) > max_count:
        actor_ids = actor_ids[: max_count + 2]
        actor_ids = random.sample(actor_ids, max_count)
    return actor_ids


def _pick_location_id(store: WorldStore, provided: Optional[str] = None) -> Optional[str]:
    if provided and provided in store.world.locations:
        return provided
    if store.world.locations:
        return random.choice(list(store.world.locations.keys()))
    return None


@router.get("/world")
def get_world():
    store = _require_store()
    return asdict(store.world)


@router.get("/map")
def get_map():
    mgr = _require_manager()
    data = load_map(mgr.current_world_id, mgr.base_dir)
    return data


@router.post("/map")
def set_map(payload: Dict[str, Any]):
    mgr = _require_manager()
    save_map(mgr.current_world_id, payload, mgr.base_dir)
    # apply to world locations
    try:
        for loc in payload.get("locations", []):
            loc_id = loc.get("id")
            if not loc_id:
                continue
            if loc_id in mgr.store.world.locations:
                mgr.store.world.locations[loc_id].coords = loc.get("coords")
                mgr.store.world.locations[loc_id].description = loc.get("description", "")
                mgr.store.world.locations[loc_id].tags = loc.get("tags", mgr.store.world.locations[loc_id].tags)
            else:
                from world.persistence.world_io import _dict_to_location

                mgr.store.world.locations[loc_id] = _dict_to_location(loc)
        mgr.store.save()
    except Exception:
        pass
    return {"status": "ok"}


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
    # attach recent memory summaries for prompt use
    mems = [store.world.memories[mid] for mid in c.memory_ids if mid in store.world.memories]
    summaries = [m.summary for m in mems if "summary" in m.tags]
    data = asdict(c)
    data["memory_summaries"] = summaries[-store.memory_summary_max_items :]
    return data


@router.post("/characters/{char_id}/move")
def move_character(char_id: str, payload: Dict[str, Any]):
    store = _require_store()
    c = store.world.characters.get(char_id)
    if not c:
        raise HTTPException(status_code=404, detail="character not found")
    loc_id = payload.get("location_id")
    if loc_id and loc_id not in store.world.locations:
        raise HTTPException(status_code=404, detail="location not found")
    if loc_id:
        c.location_id = loc_id
    if payload.get("position"):
        c.position = payload.get("position")
    store.save()
    return {"id": char_id, "location_id": c.location_id, "position": c.position}


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


@router.get("/locations")
def list_locations():
    store = _require_store()
    return {"locations": [asdict(loc) for loc in store.world.locations.values()]}


@router.get("/locations/distance")
def distance(id1: str, id2: str):
    store = _require_store()
    l1 = store.world.locations.get(id1)
    l2 = store.world.locations.get(id2)
    if not l1 or not l2:
        raise HTTPException(status_code=404, detail="location not found")
    if not l1.coords or not l2.coords:
        raise HTTPException(status_code=400, detail="coords missing")
    dx = l1.coords.get("x", 0) - l2.coords.get("x", 0)
    dy = l1.coords.get("y", 0) - l2.coords.get("y", 0)
    dist = (dx * dx + dy * dy) ** 0.5
    return {"distance": dist}


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


# Scene / conversation APIs
@router.post("/scenes")
def create_scene(payload: Dict[str, Any] = Body(default_factory=dict)):
    store = _require_store()
    mgr = _require_manager()
    scene_id = payload.get("id") or new_scene_id()
    title = payload.get("title", f"Scene {scene_id}")
    loc_id = _pick_location_id(store, payload.get("location_id"))
    participants = _select_participants(store, payload.get("participants"), location_id=loc_id)
    if len(participants) < 2:
        raise HTTPException(status_code=400, detail="at least 2 participants required")
    scene = Scene(
        id=scene_id,
        title=title,
        participants=participants,
        location_id=loc_id,
        background_tags=payload.get("background_tags", []),
        max_turns=payload.get("max_turns", 6),
    )
    store.add_scene(scene)
    return {"scene_id": scene_id, "title": title}


@router.post("/scenes/{scene_id}/step")
def step_scene(scene_id: str):
    store = _require_store()
    mgr = _require_manager()
    scene = store.get_scene(scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="scene not found")
    if scene.status == "completed":
        return {"status": "completed", "turns": [asdict(t) for t in scene.turns]}

    speaker_id = scene.next_speaker()
    speaker = store.world.characters.get(speaker_id)
    if not speaker:
        raise HTTPException(status_code=400, detail=f"speaker {speaker_id} not found")

    recent = scene.turns[-5:]
    history_text = "\n".join([f"{t.speaker}: {t.utterance}" for t in recent])
    background = store.world.background
    tags = ", ".join(scene.background_tags)
    prompt = (
        f"世界背景: {background}; 标签: {tags}\n"
        f"场景: {scene.title} @ {scene.location_id}\n"
        f"角色: {speaker.name} ({speaker.role}) 性格: {speaker.traits} 状态: {speaker.states}\n"
        f"最近对话:\n{history_text}\n"
        f"{speaker.name} 现在发言/想法（用{speaker.language}，简短，无思维链）。"
        f"避免重复他人或自己的台词，补充新的信息或情绪。"
    )
    utterance = mgr.llm.generate_dialogue(prompt)
    recent_texts = {t.utterance for t in recent}
    if utterance in recent_texts:
        utterance = f"{speaker.name}换了个角度补充道：{utterance}"
    scene.add_turn(speaker_id, utterance)
    append_story(mgr.base_dir / mgr.current_world_id, scene_id, {"speaker": speaker.name, "utterance": utterance})
    return {"scene_id": scene_id, "status": scene.status, "turn": {"speaker": speaker_id, "utterance": utterance}}


@router.get("/scenes/{scene_id}/log")
def scene_log(scene_id: str):
    store = _require_store()
    scene = store.get_scene(scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="scene not found")
    return {
        "scene_id": scene.id,
        "title": scene.title,
        "status": scene.status,
        "turns": [asdict(t) for t in scene.turns],
    }


@router.post("/scenes/auto")
def auto_scene(payload: Dict[str, Any] = Body(default_factory=dict)):
    store = _require_store()
    mgr = _require_manager()
    loc_id = _pick_location_id(store, payload.get("location_id"))
    actor_ids = _select_participants(store, payload.get("participants"), location_id=loc_id)
    if len(actor_ids) < 2:
        raise HTTPException(status_code=400, detail="at least 2 participants required")
    background = store.world.background
    tags = payload.get("background_tags", [])
    gen = mgr.llm.generate_scene(background, tags, store, actor_ids)
    scene_id = new_scene_id()
    title = gen.get("title", f"Scene {scene_id}")
    location_id = gen.get("location_id") or loc_id
    max_turns = gen.get("max_turns", 6)
    bg_tags = gen.get("background_tags", tags)
    scene = Scene(
        id=scene_id,
        title=title,
        participants=actor_ids,
        location_id=location_id,
        background_tags=bg_tags if isinstance(bg_tags, list) else tags,
        max_turns=max_turns if isinstance(max_turns, int) else 6,
    )
    store.add_scene(scene)
    return {"scene_id": scene_id, "title": scene.title, "location_id": scene.location_id, "background_tags": scene.background_tags, "max_turns": scene.max_turns}


@router.post("/scenes/auto_run")
def auto_run_scene(payload: Dict[str, Any] = Body(default_factory=dict)):
    """Auto-generate a scene and run all turns until完成或 max_turns。"""
    store = _require_store()
    mgr = _require_manager()
    loc_id = _pick_location_id(store, payload.get("location_id"))
    actor_ids = _select_participants(store, payload.get("participants"), location_id=loc_id)
    if len(actor_ids) < 2:
        raise HTTPException(status_code=400, detail="at least 2 participants required")
    background = store.world.background
    tags = payload.get("background_tags", [])
    gen = mgr.llm.generate_scene(background, tags, store, actor_ids)
    scene_id = new_scene_id()
    title = gen.get("title", f"Scene {scene_id}")
    location_id = gen.get("location_id") or loc_id
    max_turns = gen.get("max_turns", 6)
    bg_tags = gen.get("background_tags", tags)
    scene = Scene(
        id=scene_id,
        title=title,
        participants=actor_ids,
        location_id=location_id,
        background_tags=bg_tags if isinstance(bg_tags, list) else tags,
        max_turns=max_turns if isinstance(max_turns, int) else 6,
    )
    store.add_scene(scene)

    # run turns
    while scene.status == "active":
        speaker_id = scene.next_speaker()
        speaker = store.world.characters.get(speaker_id)
        if not speaker:
            scene.status = "completed"
            break
        recent = scene.turns[-5:]
        history_text = "\n".join([f"{t.speaker}: {t.utterance}" for t in recent])
        background = store.world.background
        tags_text = ", ".join(scene.background_tags)
        prompt = (
            f"世界背景: {background}; 标签: {tags_text}\n"
            f"场景: {scene.title} @ {scene.location_id}\n"
            f"角色: {speaker.name} ({speaker.role}) 性格: {speaker.traits} 状态: {speaker.states}\n"
            f"最近对话:\n{history_text}\n"
            f"{speaker.name} 现在发言/想法（用{speaker.language}，简短，无思维链）。"
        )
        utterance = mgr.llm.generate_dialogue(prompt)
        scene.add_turn(speaker_id, utterance)
        append_story(mgr.base_dir / mgr.current_world_id, scene_id, {"speaker": speaker.name, "utterance": utterance})

    return {
        "scene_id": scene_id,
        "title": scene.title,
        "status": scene.status,
        "turns": [asdict(t) for t in scene.turns],
    }


# Timeline APIs
@router.post("/timelines/auto")
def auto_timeline(payload: Dict[str, Any] = Body(default_factory=dict)):
    store = _require_store()
    mgr = _require_manager()
    actor_ids = payload.get("participants") or []
    if not actor_ids:
        actor_ids = list(store.world.characters.keys())
        if len(actor_ids) >= 3:
            actor_ids = random.sample(actor_ids, 3)
        elif len(actor_ids) == 2:
            pass
    if len(actor_ids) < 2:
        raise HTTPException(status_code=400, detail="at least 2 participants required")

    background = store.world.background
    tags = payload.get("background_tags", [])
    gen = mgr.llm.generate_scene(background, tags, store, actor_ids)
    scene_id = new_scene_id()
    scene = Scene(
        id=scene_id,
        title=gen.get("title", f"Scene {scene_id}"),
        participants=actor_ids,
        location_id=gen.get("location_id") or loc_id,
        background_tags=gen.get("background_tags", tags) if isinstance(gen.get("background_tags"), list) else tags,
        max_turns=gen.get("max_turns", 6) if isinstance(gen.get("max_turns"), int) else 6,
    )
    store.add_scene(scene)
    timeline_id = new_timeline_id()
    timeline = Timeline(
        id=timeline_id,
        title=payload.get("title") or scene.title,
        scenes=[scene_id],
        current_scene_idx=0,
        status="active",
        participants=actor_ids,
        background_tags=scene.background_tags,
    )
    store.add_timeline(timeline)
    return {"timeline_id": timeline_id, "scene_id": scene_id, "title": timeline.title}


@router.post("/timelines/step")
def step_timeline(payload: Dict[str, Any] = Body(default_factory=dict)):
    store = _require_store()
    mgr = _require_manager()
    timeline_id = payload.get("timeline_id")
    timeline = None
    if timeline_id:
        timeline = store.timelines.get(timeline_id) or store.world.timelines.get(timeline_id)
    if timeline is None:
        timeline = store.get_active_timeline()
    if timeline is None:
        # auto create if none
        auto_resp = auto_timeline({})
        timeline = store.timelines.get(auto_resp["timeline_id"])
    if timeline is None:
        raise HTTPException(status_code=500, detail="timeline not found or failed to create")
    if timeline.status == "completed":
        return {"timeline_id": timeline.id, "status": "completed"}

    # get current scene
    if timeline.current_scene_idx >= len(timeline.scenes):
        timeline.status = "completed"
        return {"timeline_id": timeline.id, "status": "completed"}

    scene_id = timeline.scenes[timeline.current_scene_idx]
    scene = store.get_scene(scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="scene not found")

    # if scene completed, maybe generate next or finish
    if scene.status == "completed":
        if len(timeline.scenes) < timeline.max_scenes:
            # generate next scene with same actors
            gen = mgr.llm.generate_scene(store.world.background, timeline.background_tags, store, timeline.participants)
            new_scene = Scene(
                id=new_scene_id(),
                title=gen.get("title", f"Scene {len(timeline.scenes)+1}"),
                participants=timeline.participants,
                location_id=gen.get("location_id") or _pick_location_id(store, None),
                background_tags=gen.get("background_tags", timeline.background_tags),
                max_turns=gen.get("max_turns", 6) if isinstance(gen.get("max_turns"), int) else 6,
            )
            store.add_scene(new_scene)
            timeline.scenes.append(new_scene.id)
            timeline.current_scene_idx += 1
            scene = new_scene
        else:
            timeline.status = "completed"
            return {"timeline_id": timeline.id, "status": "completed"}

    # run one turn in current scene
    speaker_id = scene.next_speaker()
    speaker = store.world.characters.get(speaker_id)
    if not speaker:
        scene.status = "completed"
        return {"timeline_id": timeline.id, "status": "scene missing speaker"}

    recent = scene.turns[-5:]
    history_text = "\n".join([f"{t.speaker}: {t.utterance}" for t in recent])
    background = store.world.background
    tags_text = ", ".join(scene.background_tags)
    prompt = (
        f"世界背景: {background}; 标签: {tags_text}\n"
        f"场景: {scene.title} @ {scene.location_id}\n"
        f"角色: {speaker.name} ({speaker.role}) 性格: {speaker.traits} 状态: {speaker.states}\n"
        f"最近对话:\n{history_text}\n"
        f"{speaker.name} 现在发言/想法（用{speaker.language}，简短，无思维链）。避免重复他人或自己的台词，补充新的信息或情绪。"
    )
    utterance = mgr.llm.generate_dialogue(prompt)
    recent_texts = {t.utterance for t in recent}
    if utterance in recent_texts:
        utterance = f"{speaker.name}换了个角度补充道：{utterance}"
    scene.add_turn(speaker_id, utterance)
    append_story(mgr.base_dir / mgr.current_world_id, scene.id, {"speaker": speaker.name, "utterance": utterance})

    # if scene done, maybe move to next index
    if scene.status == "completed":
        timeline.current_scene_idx += 1
        if timeline.current_scene_idx >= len(timeline.scenes):
            timeline.status = "completed"

    return {
        "timeline_id": timeline.id,
        "status": timeline.status,
        "scene_id": scene.id,
        "scene_status": scene.status,
        "turn": {"speaker": speaker_id, "utterance": utterance},
        "turn_count": len(scene.turns),
    }
