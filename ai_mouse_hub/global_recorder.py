from __future__ import annotations

import csv
import ctypes
import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

from pynput import keyboard, mouse

from .core import RECORDINGS, atomic_json


DEFAULT_GAMING_KEYS = frozenset("WASDQERFZXCV12345")


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


@dataclass(frozen=True)
class KeyboardEvent:
    timestamp: float
    event_type: str
    key: str
    hold_duration_ms: float = 0.0
    delay_since_previous_ms: float = 0.0
    overlap_keys: tuple[str, ...] = ()
    window_title: str = ""


class RecordedMouseEvents(list[MouseEvent]):
    """Mouse events with privacy-safe keyboard timing attached."""

    def __init__(self, mouse_events: Iterable[MouseEvent], keyboard_events: Iterable[KeyboardEvent]):
        super().__init__(mouse_events)
        self.keyboard_events = list(keyboard_events)


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


def _special_key_name(key: keyboard.Key | keyboard.KeyCode) -> str | None:
    if isinstance(key, keyboard.Key):
        raw = str(key).removeprefix("Key.")
        return raw.replace("_", " ").title()
    return None


def _character_key_name(key: keyboard.KeyCode, allowed_keys: frozenset[str]) -> str | None:
    char = getattr(key, "char", None)
    if not char or len(char) != 1:
        return None
    normalized = char.upper()
    return normalized if normalized in allowed_keys else None


class GlobalMouseRecorder:
    """Global mouse recorder plus privacy-safe keyboard timing.

    Special keys are stored by exact key name. Character keys are only stored when
    explicitly included in ``allowed_keys``. Free text is never reconstructed.
    """

    def __init__(
        self,
        on_event: Callable[[MouseEvent], None] | None = None,
        sample_interval: float = 0.008,
        allowed_keys: Iterable[str] = DEFAULT_GAMING_KEYS,
    ):
        self.on_event = on_event
        self.sample_interval = max(0.004, float(sample_interval))
        self.allowed_keys = frozenset(str(key).upper() for key in allowed_keys)
        self.events: list[MouseEvent] = []
        self.keyboard_events: list[KeyboardEvent] = []
        self.started_at = 0.0
        self.listener: mouse.Listener | None = None
        self.keyboard_listener: keyboard.Listener | None = None
        self.running = False
        self.paused = False
        self._paused_total = 0.0
        self._pause_started = 0.0
        self._last_move_at = -1.0
        self._last_keyboard_event_at: float | None = None
        self._pressed_keys: dict[str, float] = {}
        self._lock = threading.Lock()

    def _emit(self, event: MouseEvent) -> None:
        if not self.running or self.paused:
            return
        with self._lock:
            self.events.append(event)
        if self.on_event:
            self.on_event(event)

    def _emit_keyboard(self, event: KeyboardEvent) -> None:
        if not self.running or self.paused:
            return
        with self._lock:
            self.keyboard_events.append(event)

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

    def _key_name(self, key: keyboard.Key | keyboard.KeyCode) -> str | None:
        return _special_key_name(key) or _character_key_name(key, self.allowed_keys)

    def _on_key_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        if self.paused:
            return
        name = self._key_name(key)
        if name is None or name in self._pressed_keys:
            return
        now = self._time()
        delay = 0.0 if self._last_keyboard_event_at is None else max(0.0, (now - self._last_keyboard_event_at) * 1000.0)
        overlaps = tuple(sorted(self._pressed_keys))
        self._pressed_keys[name] = now
        self._last_keyboard_event_at = now
        self._emit_keyboard(KeyboardEvent(now, "key_down", name, delay_since_previous_ms=delay, overlap_keys=overlaps, window_title=active_window_title()))

    def _on_key_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        if self.paused:
            return
        name = self._key_name(key)
        if name is None:
            return
        now = self._time()
        started = self._pressed_keys.pop(name, None)
        if started is None:
            return
        delay = 0.0 if self._last_keyboard_event_at is None else max(0.0, (now - self._last_keyboard_event_at) * 1000.0)
        overlaps = tuple(sorted(self._pressed_keys))
        self._last_keyboard_event_at = now
        self._emit_keyboard(KeyboardEvent(now, "key_up", name, hold_duration_ms=max(0.0, (now - started) * 1000.0), delay_since_previous_ms=delay, overlap_keys=overlaps, window_title=active_window_title()))

    def start(self) -> None:
        if self.running:
            return
        self.events.clear()
        self.keyboard_events.clear()
        self._pressed_keys.clear()
        self.started_at = time.perf_counter()
        self._paused_total = 0.0
        self._pause_started = 0.0
        self._last_move_at = -1.0
        self._last_keyboard_event_at = None
        self.running = True
        self.paused = False
        self.listener = mouse.Listener(on_move=self._on_move, on_click=self._on_click, on_scroll=self._on_scroll)
        self.keyboard_listener = keyboard.Listener(on_press=self._on_key_press, on_release=self._on_key_release)
        self.listener.start()
        self.keyboard_listener.start()

    def pause(self) -> None:
        if self.running and not self.paused:
            self.paused = True
            self._pause_started = time.perf_counter()
            self._pressed_keys.clear()

    def resume(self) -> None:
        if self.running and self.paused:
            self._paused_total += time.perf_counter() - self._pause_started
            self._pause_started = 0.0
            self.paused = False
            self._last_move_at = -1.0
            self._last_keyboard_event_at = None

    def stop(self) -> RecordedMouseEvents:
        if self.paused:
            self.resume()
        self.running = False
        for listener_name in ("listener", "keyboard_listener"):
            listener = getattr(self, listener_name)
            if listener is not None:
                listener.stop()
                listener.join(timeout=2.0)
                setattr(self, listener_name, None)
        self._pressed_keys.clear()
        with self._lock:
            return RecordedMouseEvents(self.events, self.keyboard_events)


def save_global_recording(label: str, events: list[MouseEvent]) -> Path:
    if len(events) < 2:
        raise ValueError("De opname bevat te weinig muisdata.")
    keyboard_events: list[KeyboardEvent] = list(getattr(events, "keyboard_events", []))
    clean_label = label.strip() or "Unlabelled"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    folder = RECORDINGS / f"{stamp}_{clean_label.lower().replace(' ', '_')}"
    folder.mkdir(parents=True, exist_ok=False)

    with (folder / "points.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "x", "y", "event_type", "button", "pressed", "scroll_dx", "scroll_dy", "window_title"])
        for event in events:
            writer.writerow([round(event.timestamp, 6), event.x, event.y, event.event_type, event.button,
                             "" if event.pressed is None else int(event.pressed), event.scroll_dx, event.scroll_dy,
                             event.window_title])

    with (folder / "keyboard_events.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "event_type", "key", "hold_duration_ms", "delay_since_previous_ms", "overlap_keys", "window_title"])
        for event in keyboard_events:
            writer.writerow([round(event.timestamp, 6), event.event_type, event.key, round(event.hold_duration_ms, 3),
                             round(event.delay_since_previous_ms, 3), "+".join(event.overlap_keys), event.window_title])

    timeline: list[tuple[float, list[object]]] = []
    for event in events:
        detail = event.button or (f"{event.scroll_dx},{event.scroll_dy}" if event.event_type == "scroll" else "")
        timeline.append((event.timestamp, [round(event.timestamp, 6), "mouse", event.event_type, detail, event.x, event.y, "", "", event.window_title]))
    for event in keyboard_events:
        timeline.append((event.timestamp, [round(event.timestamp, 6), "keyboard", event.event_type, event.key, "", "",
                                           round(event.hold_duration_ms, 3), "+".join(event.overlap_keys), event.window_title]))
    timeline.sort(key=lambda item: item[0])
    with (folder / "input_timeline.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "source", "event_type", "detail", "x", "y", "hold_duration_ms", "overlap_keys", "window_title"])
        for _, row in timeline:
            writer.writerow(row)

    duration = max(0.0, events[-1].timestamp - events[0].timestamp)
    bounds = virtual_screen_bounds()
    titles = sorted({event.window_title for event in [*events, *keyboard_events] if event.window_title})
    key_counts: dict[str, int] = {}
    for event in keyboard_events:
        if event.event_type == "key_down":
            key_counts[event.key] = key_counts.get(event.key, 0) + 1
    atomic_json(folder / "metadata.json", {
        "session_id": folder.name,
        "label": clean_label,
        "created": datetime.now().isoformat(timespec="seconds"),
        "duration_s": duration,
        "point_count": len(events),
        "keyboard_event_count": len(keyboard_events),
        "key_down_counts": key_counts,
        "included": True,
        "recording_scope": "global_mouse_and_safe_keyboard_timing",
        "virtual_screen": {"left": bounds[0], "top": bounds[1], "width": bounds[2], "height": bounds[3]},
        "window_titles": titles[:100],
        "privacy": {
            "keyboard_timing_recorded": True,
            "special_keys_recorded": True,
            "allowed_character_keys": sorted(DEFAULT_GAMING_KEYS),
            "free_text_recorded": False,
            "typed_text_reconstructed": False,
        },
    })
    return folder
