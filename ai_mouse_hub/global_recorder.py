from __future__ import annotations

import csv
import ctypes
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from pynput import mouse

from .core import RECORDINGS, atomic_json


@dataclass(frozen=True)
class MouseEvent:
    timestamp: float
    event_type: str
    x: float
    y: float
    button: str = ""
    pressed: bool | None = None
    scroll_dx: float = 0.0
    scroll_dy: float = 0.0
    window_title: str = ""


def active_window_title() -> str:
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value[:300]
    except Exception:
        return ""


def virtual_screen_bounds() -> tuple[int, int, int, int]:
    try:
        user32 = ctypes.windll.user32
        return (
            int(user32.GetSystemMetrics(76)),
            int(user32.GetSystemMetrics(77)),
            max(1, int(user32.GetSystemMetrics(78))),
            max(1, int(user32.GetSystemMetrics(79))),
        )
    except Exception:
        return (0, 0, 1920, 1080)


class GlobalMouseRecorder:
    """Global mouse-only recorder. It never records keys or typed text."""

    def __init__(self, on_event: Callable[[MouseEvent], None] | None = None, sample_interval: float = 0.008):
        self.on_event = on_event
        self.sample_interval = max(0.004, float(sample_interval))
        self.events: list[MouseEvent] = []
        self.started_at = 0.0
        self.listener: mouse.Listener | None = None
        self.running = False
        self.paused = False
        self._paused_total = 0.0
        self._pause_started = 0.0
        self._last_move_at = -1.0
        self._lock = threading.Lock()

    def _emit(self, event: MouseEvent) -> None:
        if not self.running or self.paused:
            return
        with self._lock:
            self.events.append(event)
        if self.on_event:
            self.on_event(event)

    def _time(self) -> float:
        paused_now = time.perf_counter() - self._pause_started if self.paused else 0.0
        return max(0.0, time.perf_counter() - self.started_at - self._paused_total - paused_now)

    @property
    def elapsed(self) -> float:
        return self._time()

    def _on_move(self, x: int, y: int) -> None:
        if self.paused:
            return
        now = self._time()
        if self._last_move_at >= 0 and now - self._last_move_at < self.sample_interval:
            return
        self._last_move_at = now
        self._emit(MouseEvent(now, "move", float(x), float(y), window_title=active_window_title()))

    def _on_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        self._emit(MouseEvent(self._time(), "click", float(x), float(y), str(button), bool(pressed), window_title=active_window_title()))

    def _on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        self._emit(MouseEvent(self._time(), "scroll", float(x), float(y), scroll_dx=float(dx), scroll_dy=float(dy), window_title=active_window_title()))

    def start(self) -> None:
        if self.running:
            return
        self.events.clear()
        self.started_at = time.perf_counter()
        self._paused_total = 0.0
        self._pause_started = 0.0
        self._last_move_at = -1.0
        self.running = True
        self.paused = False
        self.listener = mouse.Listener(on_move=self._on_move, on_click=self._on_click, on_scroll=self._on_scroll)
        self.listener.start()

    def pause(self) -> None:
        if self.running and not self.paused:
            self.paused = True
            self._pause_started = time.perf_counter()

    def resume(self) -> None:
        if self.running and self.paused:
            self._paused_total += time.perf_counter() - self._pause_started
            self._pause_started = 0.0
            self.paused = False
            self._last_move_at = -1.0

    def stop(self) -> list[MouseEvent]:
        if self.paused:
            self.resume()
        self.running = False
        if self.listener is not None:
            self.listener.stop()
            self.listener.join(timeout=2.0)
            self.listener = None
        with self._lock:
            return list(self.events)


def save_global_recording(label: str, events: list[MouseEvent]) -> Path:
    if len(events) < 2:
        raise ValueError("De opname bevat te weinig muisdata.")
    clean_label = label.strip() or "Unlabelled"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    folder = RECORDINGS / f"{stamp}_{clean_label.lower().replace(' ', '_')}"
    folder.mkdir(parents=True, exist_ok=False)
    with (folder / "points.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "x", "y", "event_type", "button", "pressed", "scroll_dx", "scroll_dy", "window_title"])
        for event in events:
            writer.writerow([
                round(event.timestamp, 6), event.x, event.y, event.event_type, event.button,
                "" if event.pressed is None else int(event.pressed), event.scroll_dx, event.scroll_dy,
                event.window_title,
            ])
    duration = max(0.0, events[-1].timestamp - events[0].timestamp)
    bounds = virtual_screen_bounds()
    titles = sorted({event.window_title for event in events if event.window_title})
    atomic_json(folder / "metadata.json", {
        "session_id": folder.name,
        "label": clean_label,
        "created": datetime.now().isoformat(timespec="seconds"),
        "duration_s": duration,
        "point_count": len(events),
        "included": True,
        "recording_scope": "global_mouse_only",
        "virtual_screen": {"left": bounds[0], "top": bounds[1], "width": bounds[2], "height": bounds[3]},
        "window_titles": titles[:100],
        "privacy": {"keyboard_recorded": False, "typed_text_recorded": False},
    })
    return folder
