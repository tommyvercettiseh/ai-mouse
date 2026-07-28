from __future__ import annotations

import math
import time
import tkinter as tk

import customtkinter as ctk

from .aim_metrics import analyze_attempt, inside_target
from .aim_scheduler import BalancedTargetScheduler
from .gaming import GamingCalibration, RelativeViewTracker, load_calibration, save_calibration
from .models import TargetSpec
from .profile_builder import build_master_profile
from .raw_input import RawMouseListener
from .session_store import SessionWriter
from .theme import BORDER, GREEN, MUTED, PINK, PURPLE, SURFACE, SURFACE_2, TEXT


class AimLabPage(ctk.CTkFrame):
    """Balanced Aim Lab embedded in the main hub."""

    def __init__(self, master, on_profile_updated=None):
        super().__init__(master, fg_color="transparent")
        self.on_profile_updated = on_profile_updated
        self.scheduler = BalancedTargetScheduler()
        self.writer: SessionWriter | None = None
        self.target: TargetSpec | None = None
        self.path: list[tuple[float, float, float]] = []
        self.last_xy: tuple[float, float] | None = None
        self.click_down_t: float | None = None
        self.miss_count = 0
        self._session_start = 0.0
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, minsize=260)
        self.grid_rowconfigure(0, weight=1)
        card = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=20)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.canvas = tk.Canvas(card, bg="#080C18", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True, padx=12, pady=12)
        self.canvas.bind("<Motion>", self._motion)
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<Button-3>", self._reset_current)
        self.canvas.bind("<Configure>", lambda _event: self._render())

        panel = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=20)
        panel.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(panel, text="Aim Lab", text_color=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=18, pady=(20, 4))
        ctk.CTkLabel(panel, text="Everything is balanced automatically.", text_color=MUTED, wraplength=220).pack(anchor="w", padx=18, pady=(0, 18))
        self.timer = ctk.CTkLabel(panel, text="00:00:00", text_color=TEXT, font=("Segoe UI", 30, "bold"))
        self.timer.pack(pady=12)
        ctk.CTkButton(panel, text="●  Record", fg_color="#D83B52", height=50, corner_radius=14, command=self.start_session).pack(fill="x", padx=16, pady=6)
        ctk.CTkButton(panel, text="■  Stop", fg_color=SURFACE_2, border_color=BORDER, border_width=1, height=46, corner_radius=14, command=self.stop_session).pack(fill="x", padx=16, pady=6)
        self.info = ctk.CTkLabel(panel, text="Press Record and click the targets.", text_color=MUTED, wraplength=220)
        self.info.pack(padx=18, pady=18)

    def start_session(self) -> None:
        if self.writer is not None:
            return
        self.writer = SessionWriter(kind="aim_lab", context="balanced")
        self.scheduler = BalancedTargetScheduler()
        self._session_start = time.perf_counter()
        self.last_xy = None
        self._spawn_target()
        self._update_timer()

    def stop_session(self) -> None:
        if self.writer is None:
            return
        folder = self.writer.finish({"balanced_scheduler": True, "embedded_in_hub": True})
        self.writer = None
        self.target = None
        self.info.configure(text=f"Saved: {folder.name}")
        build_master_profile()
        if self.on_profile_updated:
            self.on_profile_updated()
        self._render()

    def _elapsed(self) -> float:
        return max(0.0, time.perf_counter() - self._session_start)

    def _update_timer(self) -> None:
        if self.writer is None:
            return
        elapsed = int(self._elapsed())
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.timer.configure(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        self.after(250, self._update_timer)

    def _spawn_target(self) -> None:
        if self.writer is None:
            return
        width = max(320, self.canvas.winfo_width())
        height = max(240, self.canvas.winfo_height())
        previous = self.last_xy or (width / 2, height / 2)
        self.target = self.scheduler.next_target(previous, width, height, self._elapsed())
        self.path = [(self._elapsed(), previous[0], previous[1])]
        self.miss_count = 0
        self._render()

    def _render(self) -> None:
        self.canvas.delete("all")
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        for x in range(0, width, 48):
            self.canvas.create_line(x, 0, x, height, fill="#10182A")
        for y in range(0, height, 48):
            self.canvas.create_line(0, y, width, y, fill="#10182A")
        if not self.target:
            self.canvas.create_text(width / 2, height / 2, text="Press Record", fill="#65718B", font=("Segoe UI", 26, "bold"))
            return
        cx, cy, r = self.target.center_x, self.target.center_y, self.target.radius
        if self.target.shape == "circle":
            self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#24134C", outline=PURPLE, width=3)
        elif self.target.shape == "square":
            self.canvas.create_rectangle(cx-r, cy-r, cx+r, cy+r, fill="#102E34", outline="#45E6C1", width=3)
        else:
            self.canvas.create_polygon(cx, cy-r, cx-r, cy+r, cx+r, cy+r, fill="#35152F", outline=PINK, width=3)

    def _motion(self, event) -> None:
        if self.writer is None or self.target is None:
            return
        point = (self._elapsed(), float(event.x), float(event.y))
        self.path.append(point)
        self.last_xy = (float(event.x), float(event.y))
        if len(self.path) >= 2:
            left, right = self.path[-2], self.path[-1]
            self.canvas.create_line(left[1], left[2], right[1], right[2], fill="#8E72FF", width=2)
        self.writer.write_event({"t": round(point[0], 6), "type": "move", "x": event.x, "y": event.y, "target_id": self.target.target_id})

    def _press(self, event) -> None:
        if self.writer is None or self.target is None:
            return
        self.click_down_t = self._elapsed()
        self.writer.write_event({"t": round(self.click_down_t, 6), "type": "click", "pressed": True, "button": "left", "x": event.x, "y": event.y, "target_id": self.target.target_id})

    def _release(self, event) -> None:
        if self.writer is None or self.target is None or self.click_down_t is None:
            return
        up_t = self._elapsed()
        click_xy = (float(event.x), float(event.y))
        self.writer.write_event({"t": round(up_t, 6), "type": "click", "pressed": False, "button": "left", "x": event.x, "y": event.y, "hold_ms": round((up_t - self.click_down_t) * 1000, 3), "target_id": self.target.target_id})
        if not inside_target(event.x, event.y, self.target):
            self.miss_count += 1
            self.click_down_t = None
            return
        result = analyze_attempt(self.path, self.target, self.click_down_t, up_t, click_xy, self.miss_count)
        self.writer.write_target(result)
        self.last_xy = click_xy
        self.click_down_t = None
        self.after(130, self._spawn_target)

    def _reset_current(self, event) -> None:
        if self.writer is None:
            return
        self.path = [(self._elapsed(), float(event.x), float(event.y))]
        self.last_xy = (float(event.x), float(event.y))
        self.miss_count += 1


class Gaming360Page(ctk.CTkFrame):
    """Embedded raw-input calibration and live virtual rotation view."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.total_x = 0
        self.total_y = 0
        self.capturing = False
        self.listener: RawMouseListener | None = None
        self.tracker = RelativeViewTracker(load_calibration())
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, minsize=280)
        self.grid_rowconfigure(0, weight=1)
        card = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=20)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.canvas = tk.Canvas(card, bg="#080C18", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=12)
        self.canvas.bind("<Configure>", lambda _event: self._draw())

        panel = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=20)
        panel.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(panel, text="Gaming 360°", text_color=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=18, pady=(20, 4))
        ctk.CTkLabel(panel, text="Raw relative input. Screen edges do not limit the measurement.", text_color=MUTED, wraplength=230).pack(anchor="w", padx=18, pady=(0, 18))
        self.value = ctk.CTkLabel(panel, text="0 raw counts", text_color=TEXT, font=("Segoe UI", 28, "bold"))
        self.value.pack(pady=14)
        ctk.CTkButton(panel, text="Start calibration", fg_color=PURPLE, height=48, corner_radius=14, command=self.start_capture).pack(fill="x", padx=16, pady=6)
        ctk.CTkButton(panel, text="Stop + save 360°", fg_color=GREEN, text_color="#06130D", height=48, corner_radius=14, command=self.stop_capture).pack(fill="x", padx=16, pady=6)
        self.info = ctk.CTkLabel(panel, text="Turn exactly one full horizontal rotation.", text_color=MUTED, wraplength=220)
        self.info.pack(padx=18, pady=18)

    def start_capture(self) -> None:
        if self.capturing:
            return
        self.total_x = 0
        self.total_y = 0
        self.tracker = RelativeViewTracker(load_calibration())
        self.capturing = True
        self.listener = RawMouseListener(self._raw)
        self.listener.start()

    def stop_capture(self) -> None:
        self.capturing = False
        if self.listener is not None:
            self.listener.stop()
            self.listener = None
        counts = abs(float(self.total_x))
        if counts >= 50:
            save_calibration(GamingCalibration(counts_per_360_x=counts))
            self.info.configure(text=f"Saved: {counts:,.0f} counts = 360°", text_color=GREEN)
            self.tracker = RelativeViewTracker(load_calibration())
        else:
            self.info.configure(text="Too little movement for calibration.", text_color="#E5484D")

    def _raw(self, _clock: float, dx: int, dy: int) -> None:
        if not self.capturing:
            return
        self.total_x += dx
        self.total_y += dy
        values = self.tracker.add(dx, dy)
        self.after(0, lambda: self._update(values))

    def _update(self, values: dict) -> None:
        yaw = float(values.get("yaw_deg") or 0.0)
        pitch = float(values.get("pitch_deg") or 0.0)
        raw_x = float(values.get("virtual_raw_x") or 0.0)
        raw_y = float(values.get("virtual_raw_y") or 0.0)
        if yaw or pitch:
            self.value.configure(text=f"Yaw {yaw:,.0f}°  ·  Pitch {pitch:,.0f}°")
        else:
            self.value.configure(text=f"Raw X {raw_x:,.0f}  ·  Y {raw_y:,.0f}")
        self._draw(yaw if yaw else raw_x)

    def _draw(self, yaw: float = 0.0) -> None:
        self.canvas.delete("all")
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        cx, cy = width / 2, height / 2
        radius = max(60, min(width, height) * 0.32)
        for factor in (1.0, 0.72, 0.44):
            r = radius * factor
            self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#26314A", width=2)
        angle = math.radians(yaw % 360.0 - 90.0)
        ex, ey = cx + math.cos(angle) * radius, cy + math.sin(angle) * radius
        self.canvas.create_line(cx, cy, ex, ey, fill=PURPLE, width=4)
        self.canvas.create_oval(cx-7, cy-7, cx+7, cy+7, fill="#45E6C1", outline="")

    def stop(self) -> None:
        if self.listener is not None:
            self.listener.stop()
            self.listener = None
