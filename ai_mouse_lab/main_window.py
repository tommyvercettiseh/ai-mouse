from __future__ import annotations

import os
import queue
from pathlib import Path

import customtkinter as ctk

from .calibration_window import CalibrationWindow
from .monitors import discover_monitors
from .paths import RECORDINGS_DIR, ensure_data_dirs
from .profile_builder import build_master_profile, load_profile_progress
from .recorder import MouseRecorder
from .theme import BG, BORDER, GREEN, MUTED, PURPLE, RED, SURFACE, SURFACE_2, TEXT
from .trace_player import latest_session, load_trace
from .widgets import MonitorMap, ProgressRing


class MainWindow(ctk.CTk):
    def __init__(self, open_aim_lab) -> None:
        super().__init__()
        ensure_data_dirs()
        self.title("AI Mouse Lab")
        self.geometry("1320x820")
        self.minsize(1050, 680)
        self.configure(fg_color=BG)
        self.open_aim_lab = open_aim_lab
        self.events: queue.Queue[dict] = queue.Queue()
        self.monitors = discover_monitors()
        self.recorder = MouseRecorder(self.events.put)
        self.playback_points: list[tuple[float, float, float]] = []
        self.playback_index = 0
        self.playback_started = 0.0
        self._build()
        self.after(16, self._poll_events)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, width=220, fg_color="#090E1A", corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        ctk.CTkLabel(sidebar, text="◒  AI Mouse Lab", text_color=TEXT, font=("Segoe UI", 21, "bold")).pack(anchor="w", padx=22, pady=(24, 2))
        ctk.CTkLabel(sidebar, text="Learn. Analyze. Replicate.", text_color=MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=22, pady=(0, 26))
        ctk.CTkButton(sidebar, text="Dashboard", fg_color=PURPLE, corner_radius=12, height=44, anchor="w").pack(fill="x", padx=14, pady=5)
        ctk.CTkButton(sidebar, text="Aim Lab", fg_color="transparent", hover_color=SURFACE_2, corner_radius=12, height=44, anchor="w", command=self.open_aim_lab).pack(fill="x", padx=14, pady=5)
        ctk.CTkButton(sidebar, text="Gaming 360°", fg_color="transparent", hover_color=SURFACE_2, corner_radius=12, height=44, anchor="w", command=lambda: CalibrationWindow(self)).pack(fill="x", padx=14, pady=5)
        ctk.CTkLabel(sidebar, text="Mouse only · Local data", text_color=MUTED, font=("Segoe UI", 9)).pack(side="bottom", anchor="w", padx=22, pady=22)

        body = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        body.grid(row=0, column=1, sticky="nsew", padx=18, pady=18)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(body, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ctk.CTkLabel(header, text="Your mouse. One clean profile.", text_color=TEXT, font=("Segoe UI", 28, "bold")).pack(side="left")
        self.status = ctk.CTkLabel(header, text="● Ready", text_color=GREEN, font=("Segoe UI", 11, "bold"))
        self.status.pack(side="right")

        content = ctk.CTkFrame(body, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, minsize=270)
        content.grid_rowconfigure(0, weight=1)

        self.monitor_map = MonitorMap(content, self.monitors)
        self.monitor_map.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        actions = ctk.CTkFrame(content, fg_color=SURFACE, corner_radius=20)
        actions.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(actions, text="Quick actions", text_color=TEXT, font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=18, pady=(20, 12))
        self.timer = ctk.CTkLabel(actions, text="00:00:00", text_color=TEXT, font=("Segoe UI", 32, "bold"))
        self.timer.pack(pady=(4, 14))
        self.record_button = ctk.CTkButton(actions, text="●  Record", fg_color=RED, hover_color="#C63843", corner_radius=14, height=52, command=self.start_recording)
        self.record_button.pack(fill="x", padx=16, pady=6)
        ctk.CTkButton(actions, text="■  Stop", fg_color=SURFACE_2, border_color=BORDER, border_width=1, corner_radius=14, height=48, command=self.stop_recording).pack(fill="x", padx=16, pady=6)
        ctk.CTkButton(actions, text="▶  Play trace", fg_color=SURFACE_2, border_color=BORDER, border_width=1, corner_radius=14, height=48, command=self.play_latest).pack(fill="x", padx=16, pady=6)
        ctk.CTkButton(actions, text="▣  Open recordings", fg_color=SURFACE_2, border_color=BORDER, border_width=1, corner_radius=14, height=48, command=self.open_recordings).pack(fill="x", padx=16, pady=6)
        ctk.CTkButton(actions, text="✦  Build profile", fg_color=PURPLE, corner_radius=14, height=48, command=self.build_profile).pack(fill="x", padx=16, pady=(6, 18))
        ctk.CTkFrame(actions, fg_color=BORDER, height=1).pack(fill="x", padx=18, pady=4)
        ctk.CTkLabel(actions, text="Profile", text_color=MUTED, font=("Segoe UI", 11)).pack(pady=(14, 4))
        self.progress = ProgressRing(actions, load_profile_progress())
        self.progress.pack(pady=(0, 12))
        self.session_label = ctk.CTkLabel(actions, text="Everything is logged automatically.", text_color=MUTED, wraplength=220, font=("Segoe UI", 10))
        self.session_label.pack(padx=20, pady=(0, 18))

    def start_recording(self) -> None:
        if self.recorder.running:
            return
        self.monitor_map.clear_trace()
        try:
            self.recorder.start()
        except Exception as exc:
            self.status.configure(text=f"● {exc}", text_color=RED)
            return
        self._record_started = __import__("time").perf_counter()
        self.status.configure(text="● Recording", text_color=RED)
        self._update_timer()

    def _update_timer(self) -> None:
        if not self.recorder.running:
            return
        elapsed = int(__import__("time").perf_counter() - self._record_started)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.timer.configure(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        self.after(250, self._update_timer)

    def stop_recording(self) -> None:
        folder = self.recorder.stop()
        self.status.configure(text="● Ready", text_color=GREEN)
        if folder:
            self.session_label.configure(text=f"Saved: {Path(folder).name}")
            self.build_profile(silent=True)

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                if event.get("type") == "move":
                    self.monitor_map.add_point(float(event["x"]), float(event["y"]))
        except queue.Empty:
            pass
        self.after(16, self._poll_events)

    def play_latest(self) -> None:
        folder = latest_session(RECORDINGS_DIR)
        if not folder:
            self.session_label.configure(text="No recordings yet.")
            return
        self.playback_points = load_trace(folder)
        if not self.playback_points:
            self.session_label.configure(text="Latest recording has no trace.")
            return
        self.monitor_map.clear_trace()
        self.playback_index = 0
        self.playback_started = __import__("time").perf_counter()
        self.status.configure(text="● Playing trace", text_color=PURPLE)
        self._play_step()

    def _play_step(self) -> None:
        import time

        if self.playback_index >= len(self.playback_points):
            self.status.configure(text="● Ready", text_color=GREEN)
            return
        elapsed = (time.perf_counter() - self.playback_started) * 1.35
        while self.playback_index < len(self.playback_points) and self.playback_points[self.playback_index][0] <= elapsed:
            _, x, y = self.playback_points[self.playback_index]
            self.monitor_map.add_point(x, y)
            self.playback_index += 1
        self.after(12, self._play_step)

    def open_recordings(self) -> None:
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(RECORDINGS_DIR)  # type: ignore[attr-defined]

    def build_profile(self, silent: bool = False) -> None:
        try:
            profile = build_master_profile()
            self.progress.set(int(profile["profile_progress_percent"]))
            if not silent:
                self.session_label.configure(text="Profile rebuilt from all local sessions.")
        except Exception as exc:
            self.session_label.configure(text=f"Profile error: {exc}")

    def _close(self) -> None:
        self.recorder.stop()
        self.destroy()
