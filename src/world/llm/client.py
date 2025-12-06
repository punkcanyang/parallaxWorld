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
        max_tokens: int = 256,
    ):
        self.endpoint = endpoint or os.getenv("WORLD_LLM_ENDPOINT", "http://localhost:3001/v1/chat/completions")
        self.model = model or os.getenv("WORLD_LLM_MODEL", None)
        self.temperature = float(os.getenv("WORLD_LLM_TEMPERATURE", temperature))
        self.system_prompt = system_prompt or os.getenv(
            "WORLD_LLM_SYSTEM_PROMPT",
            "请用简体中文回答，禁止输出<think>或思维链，只给最终简洁描述。",
        )
        self.timeout = float(os.getenv("WORLD_LLM_TIMEOUT", timeout))
        self.stop_tokens = os.getenv("WORLD_LLM_STOP", "<think>,</think>").split(",")
        self.max_tokens = int(os.getenv("WORLD_LLM_MAX_TOKENS", max_tokens))
        self._client = httpx.Client(timeout=self.timeout)

    @staticmethod
    def _strip_think(text: str) -> str:
        if not isinstance(text, str):
            return text
        import re

        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()

    def _memory_summaries_for_actor(self, store: WorldStore, actor_id: str, limit: int = 3) -> List[str]:
        if actor_id not in store.world.characters:
            return []
        c = store.world.characters[actor_id]
        summaries = []
        for mid in c.memory_ids:
            mem = store.world.memories.get(mid)
            if mem and "summary" in mem.tags:
                summaries.append(mem.summary)
        return summaries[-limit:]

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
                        "memory_summaries": self._memory_summaries_for_actor(store, ch.id),
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
            "stop": self.stop_tokens,
            "max_tokens": self.max_tokens,
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
            cleaned = self._strip_think(content)
            return cleaned if cleaned else "（两人简短地聊了几句，彼此点头示意。）"
        except Exception as e:
            return "（两人简短地聊了几句，彼此点头示意。）"

    def generate_incident(self, event_type: str, store: WorldStore, actors: List[str]) -> Dict:
        participants: List[Dict] = []
        for aid in actors:
            ch = store.world.characters.get(aid)
            if ch:
                participants.append(
                    {
                        "id": ch.id,
                        "name": ch.name,
                        "traits": ch.traits,
                        "memory_summaries": self._memory_summaries_for_actor(store, ch.id),
                    }
                )

        prompt = build_incident_prompt(event_type, participants)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        payload: Dict = {
            "messages": messages,
            "temperature": self.temperature,
            "stream": False,
            "stop": self.stop_tokens,
            "max_tokens": self.max_tokens,
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
            import json

            try:
                return json.loads(content)
            except Exception:
                cleaned = self._strip_think(content)
                return {"title": "incident", "description": cleaned}
        except Exception:
            return {"title": "incident", "description": "一个平凡的小插曲发生了。"}

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
            "stop": self.stop_tokens,
            "max_tokens": self.max_tokens,
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
            return self._strip_think(content)
        except Exception:
            return "（最近几条记忆被简要整理。）"
