from __future__ import annotations

import os
import threading
import time
from collections import Counter
from collections.abc import Callable
from typing import Any

from .gaming import RelativeViewTracker, load_calibration
from .mode_detector import InputModeDetector
from .monitors import discover_monitors, monitor_for_point
from .raw_input import RawMouseListener
from .session_store import SessionWriter

EventCallback = Callable[[dict[str, Any]], None]


def active_window_title() -> str:
    if os.name != "nt":
        return ""
    try:
        import ctypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value[:240]
    except Exception:
        return ""


class MouseRecorder:
    """Mouse-only global recorder. No keyboard hooks are created."""

    def __init__(self, callback: EventCallback | None = None) -> None:
        self.callback = callback
        self.monitors = discover_monitors()
        self.writer: SessionWriter | None = None
        self._listener = None
        self._raw_listener: RawMouseListener | None = None
        self._start_clock = 0.0
        self._lock = threading.Lock()
        self._counts: Counter[str] = Counter()
        self._mode_counts: Counter[str] = Counter()
        self._detector = InputModeDetector()
        self._view = RelativeViewTracker(load_calibration())
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        try:
            from pynput import mouse
        except ImportError as exc:
            raise RuntimeError("pynput ontbreekt. Start via de .bat-launcher.") from exc

        self.writer = SessionWriter(kind="recording", context="auto")
        self._start_clock = time.perf_counter()
        self._counts.clear()
        self._mode_counts.clear()
        self._detector = InputModeDetector()
        self._view = RelativeViewTracker(load_calibration())

        self._listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._listener.start()
        self._raw_listener = RawMouseListener(self._on_raw)
        self._raw_listener.start()
        self._running = True

    def _elapsed(self, absolute_clock: float | None = None) -> float:
        current = absolute_clock if absolute_clock is not None else time.perf_counter()
        return max(0.0, current - self._start_clock)

    def _emit(self, payload: dict[str, Any]) -> None:
        with self._lock:
            if self.writer is None:
                return
            self.writer.write_event(payload)
        self._counts[payload.get("type", "unknown")] += 1
        mode = str(payload.get("input_mode") or self._detector.mode)
        self._mode_counts[mode] += 1
        if self.callback:
            self.callback(payload)

    def _on_move(self, x: int, y: int) -> None:
        now = time.perf_counter()
        self._detector.add_absolute(now, x, y)
        monitor = monitor_for_point(self.monitors, x, y)
        self._emit(
            {
                "t": round(self._elapsed(now), 6),
                "type": "move",
                "x": int(x),
                "y": int(y),
                "monitor": monitor,
                "input_mode": self._detector.mode,
                "window_title": active_window_title(),
            }
        )

    def _on_click(self, x: int, y: int, button: Any, pressed: bool) -> None:
        now = time.perf_counter()
        self._emit(
            {
                "t": round(self._elapsed(now), 6),
                "type": "click",
                "x": int(x),
                "y": int(y),
                "monitor": monitor_for_point(self.monitors, x, y),
                "button": str(button).split(".")[-1],
                "pressed": bool(pressed),
                "input_mode": self._detector.mode,
                "window_title": active_window_title(),
            }
        )

    def _on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        now = time.perf_counter()
        self._emit(
            {
                "t": round(self._elapsed(now), 6),
                "type": "scroll",
                "x": int(x),
                "y": int(y),
                "monitor": monitor_for_point(self.monitors, x, y),
                "dx": int(dx),
                "dy": int(dy),
                "input_mode": self._detector.mode,
                "window_title": active_window_title(),
            }
        )

    def _on_raw(self, clock: float, dx: int, dy: int) -> None:
        self._detector.add_raw(clock, dx, dy)
        virtual = self._view.add(dx, dy)
        self._emit(
            {
                "t": round(self._elapsed(clock), 6),
                "type": "raw_move",
                "dx": int(dx),
                "dy": int(dy),
                "input_mode": self._detector.mode,
                **virtual,
            }
        )

    def stop(self) -> str | None:
        if not self._running:
            return None
        self._running = False
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        if self._raw_listener is not None:
            self._raw_listener.stop()
            self._raw_listener = None

        folder = None
        if self.writer is not None:
            dominant_mode = (
                self._mode_counts.most_common(1)[0][0]
                if self._mode_counts
                else "absolute"
            )
            folder = self.writer.finish(
                {
                    "event_types": dict(self._counts),
                    "dominant_input_mode": dominant_mode,
                    "raw_input_supported": os.name == "nt",
                    "monitors": [item.to_dict() for item in self.monitors],
                }
            )
            self.writer = None
        return str(folder) if folder else None
