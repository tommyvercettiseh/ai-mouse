from __future__ import annotations

import os
import queue
import time
from pathlib import Path

import customtkinter as ctk

from .embedded_pages import AimLabPage, Gaming360Page
from .monitors import discover_monitors
from .paths import RECORDINGS_DIR, ensure_data_dirs
from .profile_builder import build_master_profile, load_profile_progress
from .profile_replay import generate_profile_trace, load_profile
from .recorder import MouseRecorder
from .theme import BG, BORDER, GREEN, MUTED, PURPLE, RED, SURFACE, SURFACE_2, TEXT
from .trace_player import latest_session, load_trace
from .widgets import MonitorMap, ProgressRing


class MainWindow(ctk.CTk):
    def __init__(self, _open_aim_lab=None) -> None:
        super().__init__()
        ensure_data_dirs()
        self.title("AI Mouse Lab")
        self.geometry("1320x820")
        self.minsize(1050, 680)
        self.configure(fg_color=BG)
        self.events: queue.Queue[dict] = queue.Queue()
        self.monitors = discover_monitors()
        self.recorder = MouseRecorder(self.events.put)
        self.playback_points: list[tuple[float, float, float]] = []
        self.playback_index = 0
        self.playback_started = 0.0
        self.playback_running = False
        self._active_page = "dashboard"
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
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        for key, label in (("dashboard", "Dashboard"), ("aim", "Aim Lab"), ("gaming", "Gaming 360°")):
            button = ctk.CTkButton(
                sidebar,
                text=label,
                fg_color=PURPLE if key == "dashboard" else "transparent",
                hover_color=SURFACE_2,
                corner_radius=12,
                height=44,
                anchor="w",
                command=lambda name=key: self.show_page(name),
            )
            button.pack(fill="x", padx=14, pady=5)
            self.nav_buttons[key] = button
        ctk.CTkLabel(sidebar, text="Mouse only · Local data", text_color=MUTED, font=("Segoe UI", 9)).pack(side="bottom", anchor="w", padx=22, pady=22)

        body = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        body.grid(row=0, column=1, sticky="nsew", padx=18, pady=18)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(body, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.title_label = ctk.CTkLabel(header, text="Your mouse. One clean profile.", text_color=TEXT, font=("Segoe UI", 28, "bold"))
        self.title_label.pack(side="left")
        self.status = ctk.CTkLabel(header, text="● Ready", text_color=GREEN, font=("Segoe UI", 11, "bold"))
        self.status.pack(side="right")

        self.page_host = ctk.CTkFrame(body, fg_color="transparent")
        self.page_host.grid(row=1, column=0, sticky="nsew")
        self.page_host.grid_columnconfigure(0, weight=1)
        self.page_host.grid_rowconfigure(0, weight=1)

        self.dashboard_page = ctk.CTkFrame(self.page_host, fg_color="transparent")
        self.dashboard_page.grid(row=0, column=0, sticky="nsew")
        self._build_dashboard(self.dashboard_page)
        self.aim_page = AimLabPage(self.page_host, self._refresh_profile)
        self.gaming_page = Gaming360Page(self.page_host)

    def _build_dashboard(self, parent) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, minsize=270)
        parent.grid_rowconfigure(0, weight=1)

        self.monitor_map = MonitorMap(parent, self.monitors)
        self.monitor_map.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        actions = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=20)
        actions.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(actions, text="Quick actions", text_color=TEXT, font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=18, pady=(20, 12))
        self.timer = ctk.CTkLabel(actions, text="00:00:00", text_color=TEXT, font=("Segoe UI", 32, "bold"))
        self.timer.pack(pady=(4, 14))
        self.record_button = ctk.CTkButton(actions, text="●  Record", fg_color=RED, hover_color="#C63843", corner_radius=14, height=52, command=self.start_recording)
        self.record_button.pack(fill="x", padx=16, pady=6)
        ctk.CTkButton(actions, text="■  Stop", fg_color=SURFACE_2, border_color=BORDER, border_width=1, corner_radius=14, height=48, command=self.stop_recording).pack(fill="x", padx=16, pady=6)
        self.trace_button = ctk.CTkButton(actions, text="▶  Play trace", fg_color=SURFACE_2, border_color=BORDER, border_width=1, corner_radius=14, height=48, command=self.toggle_trace)
        self.trace_button.pack(fill="x", padx=16, pady=6)
        ctk.CTkButton(actions, text="↻  Replay profile", fg_color=SURFACE_2, border_color=BORDER, border_width=1, corner_radius=14, height=48, command=self.replay_profile).pack(fill="x", padx=16, pady=6)
        ctk.CTkButton(actions, text="▣  Open recordings", fg_color=SURFACE_2, border_color=BORDER, border_width=1, corner_radius=14, height=48, command=self.open_recordings).pack(fill="x", padx=16, pady=6)
        ctk.CTkButton(actions, text="✦  Build profile", fg_color=PURPLE, corner_radius=14, height=48, command=self.build_profile).pack(fill="x", padx=16, pady=(6, 18))
        ctk.CTkFrame(actions, fg_color=BORDER, height=1).pack(fill="x", padx=18, pady=4)
        ctk.CTkLabel(actions, text="Profile", text_color=MUTED, font=("Segoe UI", 11)).pack(pady=(14, 4))
        self.progress = ProgressRing(actions, load_profile_progress())
        self.progress.pack(pady=(0, 12))
        self.session_label = ctk.CTkLabel(actions, text="Everything is logged automatically.", text_color=MUTED, wraplength=220, font=("Segoe UI", 10))
        self.session_label.pack(padx=20, pady=(0, 18))

    def show_page(self, name: str) -> None:
        self.stop_trace()
        self._active_page = name
        for key, button in self.nav_buttons.items():
            button.configure(fg_color=PURPLE if key == name else "transparent")
        self.dashboard_page.grid_remove()
        self.aim_page.grid_remove()
        self.gaming_page.grid_remove()
        if name == "aim":
            self.title_label.configure(text="Aim Lab")
            self.aim_page.grid(row=0, column=0, sticky="nsew")
        elif name == "gaming":
            self.title_label.configure(text="Gaming 360°")
            self.gaming_page.grid(row=0, column=0, sticky="nsew")
        else:
            self.title_label.configure(text="Your mouse. One clean profile.")
            self.dashboard_page.grid(row=0, column=0, sticky="nsew")

    def start_recording(self) -> None:
        if self.recorder.running:
            return
        self.stop_trace()
        self.monitor_map.clear_trace()
        try:
            self.recorder.start()
        except Exception as exc:
            self.status.configure(text=f"● {exc}", text_color=RED)
            return
        self._record_started = time.perf_counter()
        self.status.configure(text="● Recording", text_color=RED)
        self._update_timer()

    def _update_timer(self) -> None:
        if not self.recorder.running:
            return
        elapsed = int(time.perf_counter() - self._record_started)
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

    def toggle_trace(self) -> None:
        if self.playback_running:
            self.stop_trace()
        else:
            self.play_latest()

    def play_latest(self) -> None:
        folder = latest_session(RECORDINGS_DIR)
        if not folder:
            self.session_label.configure(text="No recordings yet.")
            return
        points = load_trace(folder)
        if not points:
            self.session_label.configure(text="Latest recording has no trace.")
            return
        self._start_playback(points, "Playing recorded trace")

    def replay_profile(self) -> None:
        profile = load_profile()
        desktop = self.monitor_map.desktop
        start = (float(desktop.left + desktop.width * 0.18), float(desktop.top + desktop.height * 0.55))
        end = (float(desktop.left + desktop.width * 0.82), float(desktop.top + desktop.height * 0.38))
        points = generate_profile_trace(start, end, profile)
        timed = [(index / 90.0, x, y) for index, (x, y) in enumerate(points)]
        confidence = int(profile.get("profile_progress_percent", 0) or 0)
        self._start_playback(timed, f"Profile replay · {confidence}% learned")

    def _start_playback(self, points: list[tuple[float, float, float]], label: str) -> None:
        self.stop_trace(clear=False)
        self.monitor_map.clear_trace()
        self.playback_points = points
        self.playback_index = 0
        self.playback_started = time.perf_counter()
        self.playback_running = True
        self.trace_button.configure(text="■  Stop trace")
        self.status.configure(text=f"● {label}", text_color=PURPLE)
        self._play_step()

    def stop_trace(self, clear: bool = False) -> None:
        self.playback_running = False
        self.playback_points = []
        self.playback_index = 0
        if hasattr(self, "trace_button"):
            self.trace_button.configure(text="▶  Play trace")
        if clear and hasattr(self, "monitor_map"):
            self.monitor_map.clear_trace()
        if hasattr(self, "status") and not self.recorder.running:
            self.status.configure(text="● Ready", text_color=GREEN)

    def _play_step(self) -> None:
        if not self.playback_running:
            return
        if self.playback_index >= len(self.playback_points):
            self.stop_trace(clear=False)
            return
        elapsed = (time.perf_counter() - self.playback_started) * 1.35
        while self.playback_index < len(self.playback_points) and self.playback_points[self.playback_index][0] <= elapsed:
            _, x, y = self.playback_points[self.playback_index]
            self.monitor_map.add_point(x, y)
            self.playback_index += 1
        self.after(11, self._play_step)

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

    def _refresh_profile(self) -> None:
        self.progress.set(load_profile_progress())

    def _close(self) -> None:
        self.stop_trace()
        self.recorder.stop()
        self.gaming_page.stop()
        self.destroy()
