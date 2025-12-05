"""LLM client for world events using Parallax chat completions."""

import os
from typing import Dict, List

import httpx

from world.core.state import Event, WorldStore
from world.llm.prompts import build_event_reaction_prompt, build_incident_prompt, build_memory_summary_prompt


class HttpLLMClient:
    """Calls a chat-completions style endpoint and returns text."""

    def __init__(
        self,
        endpoint: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        system_prompt: str | None = None,
        timeout: float = 15.0,
    ):
        self.endpoint = endpoint or os.getenv("WORLD_LLM_ENDPOINT", "http://localhost:3001/v1/chat/completions")
        self.model = model or os.getenv("WORLD_LLM_MODEL", None)
        self.temperature = float(os.getenv("WORLD_LLM_TEMPERATURE", temperature))
        self.system_prompt = system_prompt or os.getenv(
            "WORLD_LLM_SYSTEM_PROMPT",
            "You are narrating a small town simulation. Be concise.",
        )
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def describe_event(self, event: Event, store: WorldStore) -> str:
        participants: List[dict] = []
        for aid in event.actors:
            ch = store.world.characters.get(aid)
            if ch:
                participants.append(
                    {
                        "id": ch.id,
                        "name": ch.name,
                        "language": ch.language,
                        "comprehension": ch.comprehension,
                        "traits": ch.traits,
                        "states": ch.states,
                    }
                )
        prompt = build_event_reaction_prompt(
            {
                "type": event.type,
                "location_id": event.location_id,
                "payload": event.payload,
                "world_default_language": getattr(store.world, "default_language", "zh-CN"),
                "force_default_language": getattr(store.world, "force_default_language", True),
            },
            participants,
        )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        payload: Dict = {
            "messages": messages,
            "temperature": self.temperature,
            "stream": False,
        }
        if self.model:
            payload["model"] = self.model

        try:
            resp = self._client.post(self.endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()
            # OpenAI/Parallax style: choices[0].message.content
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return content or "[empty LLM response]"
        except Exception as e:
            return f"[LLM error] {e}"

    def generate_incident(self, event_type: str, store: WorldStore, actors: List[str]) -> Dict:
        participants: List[Dict] = []
        for aid in actors:
            ch = store.world.characters.get(aid)
            if ch:
                participants.append({"id": ch.id, "name": ch.name, "traits": ch.traits})

        prompt = build_incident_prompt(event_type, participants)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        payload: Dict = {
            "messages": messages,
            "temperature": self.temperature,
            "stream": False,
        }
        if self.model:
            payload["model"] = self.model

        try:
            resp = self._client.post(self.endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            # Try to parse JSON from content
            import json

            try:
                return json.loads(content)
            except Exception:
                return {"title": "incident", "description": content}
        except Exception as e:
            return {"title": "incident", "description": f"[LLM error] {e}"}

    def summarize_memories(self, memories: List[Dict], max_items: int = 5) -> str:
        prompt = build_memory_summary_prompt(memories, max_items)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        payload: Dict = {
            "messages": messages,
            "temperature": self.temperature,
            "stream": False,
        }
        if self.model:
            payload["model"] = self.model
        try:
            resp = self._client.post(self.endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return content
        except Exception as e:
            return f"[LLM error] {e}"
