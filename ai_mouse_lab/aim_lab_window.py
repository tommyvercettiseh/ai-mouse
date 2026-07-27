from __future__ import annotations

import os
import time
import tkinter as tk

import customtkinter as ctk

from .aim_metrics import analyze_attempt, inside_target
from .aim_scheduler import BalancedTargetScheduler
from .models import TargetSpec
from .paths import AIM_LAB_DIR, ensure_data_dirs
from .profile_builder import build_master_profile, load_profile_progress
from .session_store import SessionWriter, read_jsonl
from .theme import BG, BORDER, GREEN, MUTED, PINK, PURPLE, SURFACE, SURFACE_2, TEXT
from .trace_player import latest_session
from .widgets import ProgressRing


class AimLabWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ensure_data_dirs()
        self.title("AI Mouse Aim Lab")
        self.geometry("1320x820")
        self.minsize(1020, 660)
        self.configure(fg_color=BG)
        self.scheduler = BalancedTargetScheduler()
        self.writer: SessionWriter | None = None
        self.target: TargetSpec | None = None
        self.path: list[tuple[float, float, float]] = []
        self.last_xy: tuple[float, float] | None = None
        self.click_down_t: float | None = None
        self.click_down_xy: tuple[float, float] | None = None
        self.miss_count = 0
        self.target_item_ids: list[int] = []
        self._session_start = 0.0
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, minsize=270)
        self.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(18, 10))
        ctk.CTkLabel(header, text="AI Mouse Aim Lab", text_color=TEXT, font=("Segoe UI", 26, "bold")).pack(side="left")
        ctk.CTkLabel(header, text="Auto-balanced. Just press Record.", text_color=MUTED, font=("Segoe UI", 11)).pack(side="left", padx=16)
        self.status = ctk.CTkLabel(header, text="● Ready", text_color=GREEN, font=("Segoe UI", 11, "bold"))
        self.status.pack(side="right")

        canvas_card = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=22)
        canvas_card.grid(row=1, column=0, sticky="nsew", padx=(20, 10), pady=(0, 20))
        self.canvas = tk.Canvas(canvas_card, bg="#080C18", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True, padx=12, pady=12)
        self.canvas.bind("<Motion>", self._motion)
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<Button-3>", self._reset_current)
        self.canvas.bind("<Configure>", lambda _event: self._draw_background())

        actions = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=22)
        actions.grid(row=1, column=1, sticky="nsew", padx=(10, 20), pady=(0, 20))
        ctk.CTkLabel(actions, text="Session", text_color=TEXT, font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=18, pady=(20, 8))
        self.timer = ctk.CTkLabel(actions, text="00:00:00", text_color=TEXT, font=("Segoe UI", 30, "bold"))
        self.timer.pack(pady=8)
        ctk.CTkButton(actions, text="●  Record", fg_color="#D83B52", hover_color="#B92F45", corner_radius=14, height=52, command=self.start_session).pack(fill="x", padx=16, pady=6)
        ctk.CTkButton(actions, text="■  Stop", fg_color=SURFACE_2, border_color=BORDER, border_width=1, corner_radius=14, height=48, command=self.stop_session).pack(fill="x", padx=16, pady=6)
        ctk.CTkButton(actions, text="▶  Play trace", fg_color=SURFACE_2, border_color=BORDER, border_width=1, corner_radius=14, height=48, command=self.play_trace).pack(fill="x", padx=16, pady=6)
        ctk.CTkButton(actions, text="▣  Open recordings", fg_color=SURFACE_2, border_color=BORDER, border_width=1, corner_radius=14, height=48, command=self.open_folder).pack(fill="x", padx=16, pady=6)
        ctk.CTkButton(actions, text="✦  Build profile", fg_color=PURPLE, corner_radius=14, height=48, command=self.build_profile).pack(fill="x", padx=16, pady=(6, 16))
        ctk.CTkFrame(actions, fg_color=BORDER, height=1).pack(fill="x", padx=18, pady=6)
        ctk.CTkLabel(actions, text="Profile", text_color=MUTED).pack(pady=(12, 4))
        self.progress = ProgressRing(actions, load_profile_progress())
        self.progress.pack()
        self.info = ctk.CTkLabel(actions, text="Shapes, sizes and distances are balanced automatically.", text_color=MUTED, wraplength=220, font=("Segoe UI", 10))
        self.info.pack(padx=20, pady=16)

    def _draw_background(self) -> None:
        if self.writer is not None:
            return
        self.canvas.delete("all")
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        for x in range(0, width, 48):
            self.canvas.create_line(x, 0, x, height, fill="#10182A")
        for y in range(0, height, 48):
            self.canvas.create_line(0, y, width, y, fill="#10182A")
        self.canvas.create_text(width / 2, height / 2, text="Press Record", fill="#65718B", font=("Segoe UI", 28, "bold"))

    def start_session(self) -> None:
        if self.writer is not None:
            return
        self.writer = SessionWriter(kind="aim_lab", context="balanced")
        self._session_start = time.perf_counter()
        self.scheduler = BalancedTargetScheduler()
        self.path = []
        self.last_xy = None
        self.status.configure(text="● Recording", text_color="#E5484D")
        self._spawn_target()
        self._update_timer()

    def _update_timer(self) -> None:
        if self.writer is None:
            return
        elapsed = int(time.perf_counter() - self._session_start)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.timer.configure(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        self.after(250, self._update_timer)

    def _elapsed(self) -> float:
        return max(0.0, time.perf_counter() - self._session_start)

    def _spawn_target(self) -> None:
        if self.writer is None:
            return
        width = max(320, self.canvas.winfo_width())
        height = max(240, self.canvas.winfo_height())
        previous = self.last_xy or (width / 2, height / 2)
        self.target = self.scheduler.next_target(previous, width, height, self._elapsed())
        self.path = [(self._elapsed(), previous[0], previous[1])]
        self.miss_count = 0
        self._render_target()

    def _render_target(self) -> None:
        self.canvas.delete("all")
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        for x in range(0, width, 48):
            self.canvas.create_line(x, 0, x, height, fill="#10182A")
        for y in range(0, height, 48):
            self.canvas.create_line(0, y, width, y, fill="#10182A")
        if not self.target:
            return
        cx, cy, r = self.target.center_x, self.target.center_y, self.target.radius
        if self.target.shape == "circle":
            self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#24134C", outline=PURPLE, width=3)
        elif self.target.shape == "square":
            self.canvas.create_rectangle(cx-r, cy-r, cx+r, cy+r, fill="#102E34", outline="#45E6C1", width=3)
        else:
            self.canvas.create_polygon(cx, cy-r, cx-r, cy+r, cx+r, cy+r, fill="#35152F", outline=PINK, width=3)
        self.canvas.create_oval(cx-3, cy-3, cx+3, cy+3, fill=TEXT, outline="")

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
        self.click_down_xy = (float(event.x), float(event.y))
        self.writer.write_event({"t": round(self.click_down_t, 6), "type": "click", "pressed": True, "button": "left", "x": event.x, "y": event.y, "target_id": self.target.target_id})

    def _release(self, event) -> None:
        if self.writer is None or self.target is None or self.click_down_t is None:
            return
        up_t = self._elapsed()
        click_xy = (float(event.x), float(event.y))
        self.writer.write_event({"t": round(up_t, 6), "type": "click", "pressed": False, "button": "left", "x": event.x, "y": event.y, "target_id": self.target.target_id})
        if not inside_target(event.x, event.y, self.target):
            self.miss_count += 1
            self.canvas.create_oval(event.x-4, event.y-4, event.x+4, event.y+4, fill="#E5484D", outline="")
            self.path = [(up_t, float(event.x), float(event.y))]
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

    def stop_session(self) -> None:
        if self.writer is None:
            return
        folder = self.writer.finish({"balanced_scheduler": True})
        self.writer = None
        self.target = None
        self.status.configure(text="● Ready", text_color=GREEN)
        self.info.configure(text=f"Saved: {folder.name}")
        self.build_profile(silent=True)
        self._draw_background()

    def play_trace(self) -> None:
        folder = latest_session(AIM_LAB_DIR)
        if not folder:
            self.info.configure(text="No Aim Lab session yet.")
            return
        rows = read_jsonl(folder / "targets.jsonl")
        paths = [row.get("path", []) for row in rows if row.get("path")]
        if not paths:
            self.info.configure(text="No trace found.")
            return
        self.canvas.delete("all")
        palette = (PURPLE, "#45E6C1", PINK)
        for index, path in enumerate(paths[-40:]):
            points = [(float(row[1]), float(row[2])) for row in path if len(row) >= 3]
            if len(points) >= 2:
                self.canvas.create_line(*[v for point in points for v in point], fill=palette[index % len(palette)], width=2, smooth=True)
        self.info.configure(text=f"Playing {len(paths[-40:])} recorded target traces.")

    def open_folder(self) -> None:
        AIM_LAB_DIR.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(AIM_LAB_DIR)  # type: ignore[attr-defined]

    def build_profile(self, silent: bool = False) -> None:
        profile = build_master_profile()
        self.progress.set(int(profile["profile_progress_percent"]))
        if not silent:
            self.info.configure(text="Profile rebuilt from all local sessions.")

    def _close(self) -> None:
        if self.writer is not None:
            self.stop_session()
        self.destroy()
