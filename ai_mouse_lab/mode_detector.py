from __future__ import annotations

import math
from collections import deque


class InputModeDetector:
    """Detect relative game input without inspecting keyboard or screen content."""

    def __init__(self, window_s: float = 1.0) -> None:
        self.window_s = float(window_s)
        self.absolute: deque[tuple[float, float]] = deque()
        self.raw: deque[tuple[float, float]] = deque()
        self.recenters: deque[float] = deque()
        self._last_xy: tuple[float, float] | None = None

    def _trim(self, now: float) -> None:
        cutoff = now - self.window_s
        while self.absolute and self.absolute[0][0] < cutoff:
            self.absolute.popleft()
        while self.raw and self.raw[0][0] < cutoff:
            self.raw.popleft()
        while self.recenters and self.recenters[0] < cutoff:
            self.recenters.popleft()

    def add_absolute(self, t: float, x: float, y: float) -> None:
        if self._last_xy is not None:
            distance = math.hypot(x - self._last_xy[0], y - self._last_xy[1])
            self.absolute.append((t, distance))
            # Very large instantaneous jumps are commonly game recenter warps.
            if distance >= 250.0:
                self.recenters.append(t)
        self._last_xy = (x, y)
        self._trim(t)

    def add_raw(self, t: float, dx: float, dy: float) -> None:
        self.raw.append((t, math.hypot(dx, dy)))
        self._trim(t)

    @property
    def mode(self) -> str:
        raw_total = sum(value for _, value in self.raw)
        absolute_total = sum(value for _, value in self.absolute)
        if len(self.recenters) >= 2:
            return "gaming"
        if raw_total >= 300.0 and absolute_total <= raw_total * 0.18:
            return "gaming"
        return "absolute"
