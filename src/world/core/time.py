"""Time and tick management for the world simulation."""

import time
from dataclasses import dataclass
from typing import Callable


@dataclass
class ClockConfig:
    tick_seconds: float = 1.0  # real seconds per tick before scaling
    time_scale: float = 1.0  # multiplier; 2.0 = 2x speed


class SimulationClock:
    """Simple clock to control tick pacing and time scaling."""

    def __init__(self, config: ClockConfig | None = None):
        self.config = config or ClockConfig()
        self._running = False
        self._tick = 0

    @property
    def tick(self) -> int:
        return self._tick

    def set_time_scale(self, scale: float) -> None:
        self.config.time_scale = max(0.1, scale)

    def step(self, on_tick: Callable[[int], None]) -> None:
        """Advance one tick and invoke the callback."""
        self._tick += 1
        on_tick(self._tick)

    def loop(self, on_tick: Callable[[int], None]) -> None:
        """Run continuous ticks until stopped."""
        self._running = True
        while self._running:
            start = time.time()
            self.step(on_tick)
            elapsed = time.time() - start
            sleep_for = max(0.0, (self.config.tick_seconds / self.config.time_scale) - elapsed)
            if sleep_for:
                time.sleep(sleep_for)

    def stop(self) -> None:
        self._running = False

