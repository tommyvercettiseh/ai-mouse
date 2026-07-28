from __future__ import annotations

import time
import tkinter as tk
from collections import deque

import customtkinter as ctk

from .models import MonitorInfo
from .monitors import monitor_rect_on_canvas, screen_to_canvas, virtual_desktop
from .theme import BG, BORDER, GREEN, MUTED, PURPLE, SURFACE, TEXT


TRACE_PALETTE = (
    "#15152D",
    "#211B46",
    "#30205F",
    "#432777",
    "#5A2F91",
    "#7339AD",
    "#8E45C8",
    "#A858E1",
    "#C16CF4",
)


class MonitorMap(ctk.CTkFrame):
    """Privacy-safe monitor map with a fixed-rate fading trace renderer."""

    def __init__(self, master, monitors: list[MonitorInfo], **kwargs):
        super().__init__(master, fg_color=SURFACE, corner_radius=20, **kwargs)
        self.monitors = monitors
        self.desktop = virtual_desktop(monitors)
        self.trace: deque[tuple[float, float, float]] = deque(maxlen=3200)
        self.cursor_xy: tuple[float, float] | None = None
        self.fade_seconds = 1.6
        self._dirty = True
        self.canvas = tk.Canvas(self, bg=SURFACE, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=12)
        self.canvas.bind("<Configure>", lambda _event: self._mark_dirty())
        self.after(16, self._render_loop)

    def _mark_dirty(self) -> None:
        self._dirty = True

    def clear_trace(self) -> None:
        self.trace.clear()
        self.cursor_xy = None
        self._dirty = True

    def add_point(self, x: float, y: float, timestamp: float | None = None) -> None:
        self.cursor_xy = (x, y)
        self.trace.append((timestamp if timestamp is not None else time.perf_counter(), x, y))
        self._dirty = True

    def set_trace(self, points: list[tuple[float, float]]) -> None:
        now = time.perf_counter()
        self.trace.clear()
        for index, (x, y) in enumerate(points[-2500:]):
            age = (len(points[-2500:]) - index) / 120.0
            self.trace.append((now - age, x, y))
        self.cursor_xy = points[-1] if points else None
        self._dirty = True

    def _render_loop(self) -> None:
        now = time.perf_counter()
        while self.trace and now - self.trace[0][0] > self.fade_seconds:
            self.trace.popleft()
            self._dirty = True
        if self._dirty:
            self.redraw(now)
            self._dirty = False
        self.after(16, self._render_loop)

    def redraw(self, now: float | None = None) -> None:
        now = now if now is not None else time.perf_counter()
        canvas = self.canvas
        width, height = max(2, canvas.winfo_width()), max(2, canvas.winfo_height())
        canvas.delete("all")

        for x in range(0, width, 42):
            canvas.create_line(x, 0, x, height, fill="#111A2C")
        for y in range(0, height, 42):
            canvas.create_line(0, y, width, y, fill="#111A2C")

        for monitor in self.monitors:
            x1, y1, x2, y2 = monitor_rect_on_canvas(
                monitor, self.desktop, width, height, padding=22
            )
            canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                fill="#0A1020",
                outline=PURPLE if monitor.primary else BORDER,
                width=2,
            )
            canvas.create_text(
                x1 + 14,
                y1 + 14,
                text=f"Screen {monitor.index}  {monitor.width}×{monitor.height}",
                fill=TEXT,
                anchor="nw",
                font=("Segoe UI", 10, "bold"),
            )

        points = list(self.trace)
        mapped = [
            (
                timestamp,
                *screen_to_canvas(x, y, self.desktop, width, height, padding=22),
            )
            for timestamp, x, y in points
        ]
        for index in range(1, len(mapped)):
            left = mapped[index - 1]
            right = mapped[index]
            age = max(0.0, now - right[0])
            strength = 1.0 - min(1.0, age / self.fade_seconds)
            palette_index = min(len(TRACE_PALETTE) - 1, int(strength * len(TRACE_PALETTE)))
            canvas.create_line(
                left[1],
                left[2],
                right[1],
                right[2],
                fill=TRACE_PALETTE[palette_index],
                width=2 + int(strength * 2),
                smooth=True,
            )

        if self.cursor_xy:
            cx, cy = screen_to_canvas(
                self.cursor_xy[0],
                self.cursor_xy[1],
                self.desktop,
                width,
                height,
                padding=22,
            )
            canvas.create_oval(cx - 9, cy - 9, cx + 9, cy + 9, fill=GREEN, outline="")
            canvas.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill=BG, outline="")


class ProgressRing(ctk.CTkFrame):
    def __init__(self, master, value: int = 0, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.value = max(0, min(100, int(value)))
        self.canvas = tk.Canvas(self, width=112, height=112, bg=SURFACE, highlightthickness=0)
        self.canvas.pack()
        self.redraw()

    def set(self, value: int) -> None:
        self.value = max(0, min(100, int(value)))
        self.redraw()

    def redraw(self) -> None:
        c = self.canvas
        c.delete("all")
        c.create_oval(10, 10, 102, 102, outline=BORDER, width=9)
        c.create_arc(
            10,
            10,
            102,
            102,
            start=90,
            extent=-360 * self.value / 100,
            outline=PURPLE,
            width=9,
            style="arc",
        )
        c.create_text(56, 49, text=f"{self.value}%", fill=TEXT, font=("Segoe UI", 20, "bold"))
        c.create_text(56, 73, text="learned", fill=MUTED, font=("Segoe UI", 9))
