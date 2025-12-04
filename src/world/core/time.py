"""Time and tick management for the world simulation."""

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional


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
        self._loop_thread: Optional[threading.Thread] = None
        self._on_tick: Optional[Callable[[int], None]] = None

    @property
    def tick(self) -> int:
        return self._tick

    @property
    def is_running(self) -> bool:
        return self._running

    def set_time_scale(self, scale: float) -> None:
        self.config.time_scale = max(0.1, scale)

    def step(self, on_tick: Callable[[int], None]) -> None:
        """Advance one tick and invoke the callback."""
        self._tick += 1
        on_tick(self._tick)

    def start(self, on_tick: Callable[[int], None]) -> None:
        """Start continuous ticks in background until stopped."""
        if self._running:
            return
        self._on_tick = on_tick
        self._running = True
        self._loop_thread = threading.Thread(target=self._loop, daemon=True)
        self._loop_thread.start()

    def _loop(self) -> None:
        while self._running:
            start = time.time()
            if self._on_tick is not None:
                self.step(self._on_tick)
            elapsed = time.time() - start
            sleep_for = max(0.0, (self.config.tick_seconds / self.config.time_scale) - elapsed)
            if sleep_for:
                time.sleep(sleep_for)

    def stop(self) -> None:
        self._running = False
        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=0.1)
        self._loop_thread = None

