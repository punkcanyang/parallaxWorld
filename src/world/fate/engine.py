"""Fate engine: evaluates rules, schedules and resolves events."""

import random
import uuid
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from world.core.state import Event, Memory, WorldStore


@dataclass
class FateRule:
    id: str
    trigger: str  # e.g., "tick", "probabilistic", "tag:famine"
    weight: float = 1.0
    condition: Optional[Callable[[WorldStore], bool]] = None
    factory: Optional[Callable[[WorldStore, int], List[Event]]] = None


class FateEngine:
    def __init__(self, store: WorldStore, llm_client):
        self.store = store
        self.rules: List[FateRule] = []
        self.event_queue: Dict[str, Event] = {}
        self.llm = llm_client

    def register_rule(self, rule: FateRule) -> None:
        self.rules.append(rule)

    def register_many(self, rules: List[FateRule]) -> None:
        for r in rules:
            self.register_rule(r)

    def on_tick(self, tick_id: int) -> List[Event]:
        """Evaluate rules and enqueue events. Returns newly enqueued events."""
        new_events: List[Event] = []
        for rule in self.rules:
            if rule.trigger not in ("tick",):
                continue
            if rule.condition and not rule.condition(self.store):
                continue
            if rule.factory:
                events = rule.factory(self.store, tick_id)
                for ev in events:
                    self.store.add_event(ev)
                    self.event_queue[ev.id] = ev
                new_events.extend(events)
        return new_events

    def pop_due_events(self, current_tick: int) -> List[Event]:
        due = []
        for ev in list(self.event_queue.values()):
            if ev.scheduled_for <= current_tick and ev.status == "scheduled":
                ev.status = "ready"
                due.append(ev)
                self.event_queue.pop(ev.id, None)
        return due

    def process_due_events(self, current_tick: int) -> List[Dict]:
        """Pop due events, call AI for outcomes, mark resolved, log results."""
        due = self.pop_due_events(current_tick)
        processed: List[Dict] = []
        for ev in due:
            if not ev.payload.get("incident"):
                ev.payload["incident"] = self.llm.generate_incident(ev.type, self.store, ev.actors)
            result = {
                "id": ev.id,
                "type": ev.type,
                "actors": ev.actors,
                "location_id": ev.location_id,
                "tick": current_tick,
                "incident": ev.payload.get("incident"),
            }
            dialogue = self.llm.describe_event(ev, self.store)
            ev.status = "resolved"
            result["dialogue"] = dialogue
            # Apply effects (mood/traits/relationships deltas)
            applied_effects = self._apply_effects(ev)
            if applied_effects:
                result["effects_applied"] = applied_effects
            drift = self._apply_personality_drift(ev)
            if drift:
                result["personality_drift"] = drift
            new_memories = self._record_memories(ev, dialogue)
            if new_memories:
                result["memories"] = new_memories
                summaries = self._maybe_summarize_memories(ev.actors)
                if summaries:
                    result["memory_summaries"] = summaries
            self.store.append_log(result)
            processed.append(result)
        return processed

    def _apply_effects(self, event: Event) -> List[Dict]:
        """Apply event.effects to characters or world. effect schema: {target, field, delta|set}."""
        applied = []
        for eff in event.effects:
            target_id = eff.get("target")
            field = eff.get("field")
            delta = eff.get("delta")
            set_value = eff.get("set")
            if not target_id or not field:
                continue
            ch = self.store.world.characters.get(target_id)
            if ch is None:
                continue
            # Decide which dict to mutate: states, traits, relationships, or attributes
            container = None
            if field.startswith("state:"):
                key = field.split(":", 1)[1]
                container = ch.states
            elif field.startswith("trait:"):
                key = field.split(":", 1)[1]
                container = ch.traits
            elif field.startswith("rel:"):
                key = field.split(":", 1)[1]
                container = ch.relationships
            elif field.startswith("attr:"):
                key = field.split(":", 1)[1]
                container = ch.attributes
            else:
                key = field
                container = ch.states

            if container is None:
                continue

            before = container.get(key, 0.0)
            if delta is not None:
                container[key] = before + delta
            elif set_value is not None:
                container[key] = set_value
            after = container.get(key, before)
            applied.append({"target": target_id, "field": field, "before": before, "after": after})

        return applied

    def _apply_personality_drift(self, event: Event) -> List[Dict]:
        """Lightweight drift based on event type and actor pairs."""
        if not event.actors:
            return []
        deltas = []
        # simple rules
        if event.type in ("random_encounter", "morning_greeting"):
            delta = 0.1
        elif event.type in ("bad_luck",):
            delta = -0.05
        else:
            delta = 0.0

        if delta == 0:
            return []

        actors = event.actors
        for i, aid in enumerate(actors):
            for bid in actors[i + 1 :]:
                a = self.store.world.characters.get(aid)
                b = self.store.world.characters.get(bid)
                if not a or not b:
                    continue
                before_ab = a.relationships.get(bid, 0.0)
                before_ba = b.relationships.get(aid, 0.0)
                a.relationships[bid] = before_ab + delta
                b.relationships[aid] = before_ba + delta
                deltas.append(
                    {
                        "pair": (aid, bid),
                        "delta": delta,
                        "before": {"a_to_b": before_ab, "b_to_a": before_ba},
                        "after": {"a_to_b": a.relationships[bid], "b_to_a": b.relationships[aid]},
                    }
                )
        return deltas

    def _record_memories(self, event: Event, dialogue: str) -> List[Dict]:
        """Create memory entries for actors and keep summaries short."""
        created = []
        for aid in event.actors:
            if aid not in self.store.world.characters:
                continue
            mem_id = str(uuid.uuid4())
            summary = dialogue[:200]
            memory = Memory(
                id=mem_id,
                owner_id=aid,
                summary=summary,
                salience=1.0,
                tags=[event.type],
                created_at=event.created_at,
            )
            self.store.add_memory(memory)
            created.append({"owner": aid, "id": mem_id, "summary": summary})
        return created

    def _maybe_summarize_memories(self, actors: List[str]) -> List[Dict]:
        summaries = []
        for aid in actors:
            count = self.store.memory_event_count.get(aid, 0)
            if count >= self.store.memory_summary_every_n:
                summary_mem = self.store.summarize_memories(self.llm, aid, limit=20)
                if summary_mem:
                    summaries.append({"owner": aid, "id": summary_mem.id, "summary": summary_mem.summary})
        return summaries



def _pick_two_characters(store: WorldStore) -> Optional[List[str]]:
    chars = list(store.world.characters.keys())
    if len(chars) < 2:
        return None
    return random.sample(chars, 2)


def _make_event(event_type: str, tick_id: int, location_id: Optional[str], actors: List[str]):
    return Event(
        id=str(uuid.uuid4()),
        type=event_type,
        created_at=tick_id,
        scheduled_for=tick_id,
        location_id=location_id,
        actors=actors,
        payload={},
    )


def build_default_rules(store: WorldStore) -> List[FateRule]:
    """Three minimal rules: morning greeting, random encounter, bad mood."""

    def morning_condition(store: WorldStore) -> bool:
        # Example: every 10 ticks as "morning"
        return store.world.epoch % 10 == 0 and len(store.world.characters) >= 1

    def morning_factory(store: WorldStore, tick: int) -> List[Event]:
        actors = _pick_two_characters(store) or list(store.world.characters.keys())[:1]
        if not actors:
            return []
        return [_make_event("morning_greeting", tick, "loc-1", actors)]

    def encounter_condition(store: WorldStore) -> bool:
        return len(store.world.characters) >= 2

    def encounter_factory(store: WorldStore, tick: int) -> List[Event]:
        actors = _pick_two_characters(store)
        if not actors:
            return []
        return [_make_event("random_encounter", tick, "loc-1", actors)]

    def bad_thing_factory(store: WorldStore, tick: int) -> List[Event]:
        if not store.world.characters:
            return []
        actor = random.choice(list(store.world.characters.keys()))
        return [_make_event("bad_luck", tick, "loc-1", [actor])]

    return [
        FateRule(id="morning-greet", trigger="tick", condition=morning_condition, factory=morning_factory, weight=1.0),
        FateRule(id="encounter", trigger="tick", condition=encounter_condition, factory=encounter_factory, weight=0.5),
        FateRule(id="bad-luck", trigger="tick", condition=None, factory=bad_thing_factory, weight=0.2),
    ]
