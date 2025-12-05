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
If participant has language, respond in that language; if force_global_language is true, respond in world.default_language. Avoid meta-thinking, only final output.
If participant has memory_summaries, reference them for context; keep responses concise.
    """.strip()


def build_incident_prompt(event_type: str, participants: List[Dict]) -> str:
    return f"""
You are creating a concrete situation for a town simulation.
Event type: {event_type}
Participants: {participants}
Give a short title and a 1-2 sentence description of a specific incident that fits this event type.
Respond as JSON: {{"title": "...", "description": "..." }}
Avoid meta-comments or explanations.
""".strip()


def build_memory_summary_prompt(memories: List[Dict], max_items: int = 5) -> str:
    return f"""
Summarize the following recent memories into a concise recap (<= {max_items} bullet points).
Keep it short and factual, no meta thinking.
Memories: {memories}
Return plain text only.
""".strip()
