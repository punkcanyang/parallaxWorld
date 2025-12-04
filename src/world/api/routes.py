"""Minimal API stubs for the world simulation."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/world")
def get_world():
    # TODO: inject store via dependency
    return {"message": "world snapshot"}


@router.post("/world/time-scale")
def set_time_scale(payload: dict):
    # TODO: update clock time scale
    return {"time_scale": payload.get("time_scale", 1.0)}


@router.post("/characters")
def create_character(payload: dict):
    return {"created": payload}


@router.get("/events")
def list_events(status: str | None = None):
    return {"events": [], "status": status}


@router.post("/events")
def create_event(payload: dict):
    return {"created": payload}


@router.post("/simulate/step")
def simulate_step():
    return {"tick": "next"}


@router.get("/logs/tail")
def logs_tail():
    return {"logs": []}

