"""World management endpoints."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from world.core.manager import MultiWorldManager
from world.core.state import WorldStore
from world.core.time import SimulationClock
from world.fate.engine import FateEngine
from world.api import routes as world_routes

router = APIRouter()

_manager: Optional[MultiWorldManager] = None


def configure_world_manager(manager: MultiWorldManager) -> None:
    global _manager
    _manager = manager
    # push current manager state into world routes
    world_routes.configure_world(manager.store, manager.clock, manager.engine, manager)


def _require_manager() -> MultiWorldManager:
    if _manager is None:
        raise HTTPException(status_code=500, detail="World manager not configured")
    return _manager


@router.get("/worlds")
def list_worlds():
    mgr = _require_manager()
    return {"worlds": mgr.list_worlds(), "current": mgr.current_world_id}


@router.post("/worlds")
def create_world(payload: Dict[str, Any]):
    mgr = _require_manager()
    world_id = payload.get("id")
    if not world_id:
        raise HTTPException(status_code=400, detail="id is required")
    name = payload.get("name", world_id)
    background = payload.get("background", "")
    default_language = payload.get("default_language", "zh-CN")
    force_default_language = bool(payload.get("force_default_language", True))
    mgr.create_world(world_id, name, background, default_language, force_default_language)
    return {"created": world_id}


@router.post("/worlds/select")
def select_world(payload: Dict[str, Any]):
    mgr = _require_manager()
    world_id = payload.get("id")
    if not world_id:
        raise HTTPException(status_code=400, detail="id is required")
    if world_id not in mgr.list_worlds():
        raise HTTPException(status_code=404, detail="world not found")
    info = mgr.select_world(world_id)
    # reconfigure world routes to new instances
    world_routes.configure_world(mgr.store, mgr.clock, mgr.engine, mgr)
    return {"selected": world_id, "info": info}

