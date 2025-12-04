"""Fate engine: evaluates rules and schedules events."""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from world.core.state import Event, WorldStore


@dataclass
class FateRule:
    id: str
    trigger: str  # e.g., "tick", "probabilistic", "tag:famine"
    weight: float = 1.0
    condition: Optional[Callable[[WorldStore], bool]] = None
    factory: Optional[Callable[[WorldStore, int], List[Event]]] = None


class FateEngine:
    def __init__(self, store: WorldStore):
        self.store = store
        self.rules: List[FateRule] = []
        self.event_queue: Dict[str, Event] = {}

    def register_rule(self, rule: FateRule) -> None:
        self.rules.append(rule)

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

