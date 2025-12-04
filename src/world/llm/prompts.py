"""Prompt templates for dialogue and reactions."""

from typing import Dict, List


def build_character_sheet_prompt(
    world_background: str,
    location: str,
    character: Dict,
    relationships: List[Dict],
    memories: List[Dict],
) -> str:
    return f"""
World: {world_background}
Location: {location}
Character: {character}
Top relationships: {relationships}
Recent memories: {memories}
Respond with intent, one line of dialogue (optional), and JSON deltas for states/traits.
    """.strip()


def build_event_reaction_prompt(event: Dict, participants: List[Dict]) -> str:
    return f"""
Event: {event}
Participants: {participants}
For each participant, give reaction text and JSON deltas to states/traits/relationships.
    """.strip()

