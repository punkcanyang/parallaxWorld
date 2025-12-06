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
If participant has memory_summaries, use them to keep story continuity; keep responses concise.
    """.strip()


def build_incident_prompt(event_type: str, participants: List[Dict]) -> str:
    return f"""
You are creating a concrete situation for a town simulation.
Event type: {event_type}
Participants: {participants}
If memory_summaries exist, use them to keep the story continuous.
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


def build_scene_prompt(background: str, tags: List[str], participants: List[Dict]) -> str:
    return f"""
你是故事编剧，需要在给定世界背景下生成一个对话场景。请用简体中文，避免思维链，只给最终结果。
世界背景: {background}
背景标签: {tags}
参与角色(含性格/状态/记忆摘要): {participants}
请输出 JSON：
{{
  "title": "场景标题",
  "location_id": "可选地点ID或描述",
  "background_tags": ["..."],
  "max_turns": 6
}}
要求：场景设定应匹配角色和背景，标题简洁，max_turns 不宜过大。
""".strip()
