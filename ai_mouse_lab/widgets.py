from __future__ import annotations

import tkinter as tk
from collections import deque

import customtkinter as ctk

from .models import MonitorInfo
from .monitors import monitor_rect_on_canvas, screen_to_canvas, virtual_desktop
from .theme import BG, BORDER, GREEN, MUTED, PURPLE, SURFACE, TEXT


class MonitorMap(ctk.CTkFrame):
    """Privacy-safe monitor overview: geometry, cursor and trace only."""

    def __init__(self, master, monitors: list[MonitorInfo], **kwargs):
        super().__init__(master, fg_color=SURFACE, corner_radius=20, **kwargs)
        self.monitors = monitors
        self.desktop = virtual_desktop(monitors)
        self.trace: deque[tuple[float, float]] = deque(maxlen=2500)
        self.cursor_xy: tuple[float, float] | None = None
        self.canvas = tk.Canvas(self, bg=SURFACE, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=12)
        self.canvas.bind("<Configure>", lambda _event: self.redraw())

    def clear_trace(self) -> None:
        self.trace.clear()
        self.cursor_xy = None
        self.redraw()

    def add_point(self, x: float, y: float) -> None:
        self.cursor_xy = (x, y)
        self.trace.append((x, y))
        self.redraw()

    def set_trace(self, points: list[tuple[float, float]]) -> None:
        self.trace.clear()
        self.trace.extend(points[-2500:])
        self.cursor_xy = points[-1] if points else None
        self.redraw()

    def redraw(self) -> None:
        canvas = self.canvas
        width, height = max(2, canvas.winfo_width()), max(2, canvas.winfo_height())
        canvas.delete("all")

        # Subtle grid instead of screenshots, preserving privacy.
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

        mapped = [
            screen_to_canvas(x, y, self.desktop, width, height, padding=22)
            for x, y in self.trace
        ]
        if len(mapped) >= 2:
            flat = [number for point in mapped for number in point]
            canvas.create_line(
                *flat,
                fill=PURPLE,
                width=3,
                smooth=True,
                splinesteps=12,
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
