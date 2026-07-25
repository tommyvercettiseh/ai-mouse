from __future__ import annotations

import os
import subprocess
import sys
import time
import tkinter as tk
from collections import deque
from tkinter import messagebox, ttk

from .core import RECORDINGS, list_sessions, load_points
from .global_recorder import GlobalMouseRecorder, MouseEvent, save_global_recording, virtual_screen_bounds
from .screen_layout import MonitorInfo, enumerate_monitors, monitor_for_point

BG = "#07101d"
PANEL = "#0d1928"
PANEL_2 = "#132238"
TEXT = "#f5f7ff"
MUTED = "#8d9bb0"
BORDER = "#20324a"
BLUE = "#3478ff"
PURPLE = "#8b4dff"
CYAN = "#18c7e8"
GREEN = "#42d67b"
RED = "#ef4a56"


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AI Mouse Hub")
        self.root.geometry("1080x720")
        self.root.minsize(900, 620)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.bounds = virtual_screen_bounds()
        self.monitors = enumerate_monitors()
        self.active_monitor: MonitorInfo | None = None
        self.recorder = GlobalMouseRecorder(on_event=self._queue_event)
        self.event_queue: deque[MouseEvent] = deque()
        self.live_trace: deque[tuple[float, float, float]] = deque(maxlen=500)
        self.sessions = []
        self.session_map: dict[str, object] = {}
        self.replay_points: list[tuple[float, float, float]] = []
        self.replay_index = 0
        self.replay_after: str | None = None
        self.replay_started = 0.0

        self._styles()
        self._build()
        self.refresh_sessions()
        self._tick()

    def _styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=PANEL, foreground=TEXT, fieldbackground=PANEL,
                        rowheight=32, bordercolor=BORDER)
        style.configure("Treeview.Heading", background=PANEL_2, foreground=MUTED, bordercolor=BORDER)
        style.map("Treeview", background=[("selected", "#203765")], foreground=[("selected", TEXT)])
        style.configure("TCombobox", fieldbackground=PANEL_2, background=PANEL_2, foreground=TEXT)

    def _button(self, parent, text, command, bg=PANEL_2, **kwargs):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=TEXT,
                         activebackground=bg, activeforeground=TEXT, disabledforeground="#5f6d82",
                         relief="flat", bd=0, cursor="hand2", font=("Segoe UI", 10, "bold"), **kwargs)

    def _build(self) -> None:
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True, padx=18, pady=16)

        header = tk.Frame(shell, bg=BG)
        header.pack(fill="x", pady=(0, 12))
        tk.Label(header, text="AI Mouse Hub", bg=BG, fg=TEXT, font=("Segoe UI", 23, "bold")).pack(side="left")
        tk.Label(header, text="v0.11.0 · lokaal", bg=BG, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(side="right")

        controls = tk.Frame(shell, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        controls.pack(fill="x", pady=(0, 12))
        row = tk.Frame(controls, bg=PANEL)
        row.pack(fill="x", padx=14, pady=12)

        self.record_btn = self._button(row, "●  Record", self.start_recording, bg=RED, padx=20, pady=9)
        self.record_btn.pack(side="left")
        self.stop_btn = self._button(row, "■  Stop + opslaan", self.stop_and_save, bg=BLUE,
                                     padx=18, pady=9, state="disabled")
        self.stop_btn.pack(side="left", padx=8)
        self.play_btn = self._button(row, "▶  Play", self.play_selected, bg=PURPLE, padx=18, pady=9)
        self.play_btn.pack(side="left")
        self._button(row, "▣  Open map", self.open_recordings_folder, padx=16, pady=9).pack(side="left", padx=8)
        self._button(row, "◎  Aim Lab", self.open_aim_lab, bg="#21498b", padx=18, pady=9).pack(side="right")

        tk.Label(row, text="Label", bg=PANEL, fg=MUTED).pack(side="right", padx=(12, 6))
        self.label_var = tk.StringVar(value="Gaming")
        ttk.Combobox(row, textvariable=self.label_var,
                     values=("Gaming", "Browsing", "Werk", "Precision"), width=11).pack(side="right")

        body = tk.Frame(shell, bg=BG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        monitor_panel = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        monitor_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        top = tk.Frame(monitor_panel, bg=PANEL)
        top.pack(fill="x", padx=14, pady=(12, 6))
        tk.Label(top, text="Schermoverzicht", bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(side="left")
        self.monitor_label = tk.Label(top, text="", bg=PANEL, fg=MUTED, font=("Segoe UI", 9))
        self.monitor_label.pack(side="right")
        self.canvas = tk.Canvas(monitor_panel, bg="#050c16", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.canvas.bind("<Configure>", lambda _e: self._redraw())
        self.position_label = tk.Label(monitor_panel, text="Muispositie: —", bg=PANEL, fg=MUTED,
                                       anchor="w", font=("Segoe UI", 9))
        self.position_label.pack(fill="x", padx=14, pady=(0, 12))

        recording_panel = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        recording_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        recording_panel.grid_rowconfigure(1, weight=1)
        recording_panel.grid_columnconfigure(0, weight=1)
        head = tk.Frame(recording_panel, bg=PANEL)
        head.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        tk.Label(head, text="Opnames", bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(side="left")
        self.status = tk.Label(head, text="● Gereed", bg=PANEL, fg=GREEN, font=("Segoe UI", 9, "bold"))
        self.status.pack(side="right")

        self.tree = ttk.Treeview(recording_panel, columns=("date", "label", "duration"), show="headings", selectmode="browse")
        for key, title, width in (("date", "Opname", 180), ("label", "Label", 95), ("duration", "Duur", 65)):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="w" if key != "duration" else "center")
        self.tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        footer = tk.Label(shell, text=f"Data: {RECORDINGS}", bg=BG, fg=MUTED, anchor="w", font=("Segoe UI", 8))
        footer.pack(fill="x", pady=(8, 0))

    def _queue_event(self, event: MouseEvent) -> None:
        self.event_queue.append(event)

    def _tick(self) -> None:
        now = time.perf_counter()
        while self.event_queue:
            event = self.event_queue.popleft()
            if event.event_type == "move":
                self.live_trace.append((now, event.x, event.y))

        try:
            x, y = float(self.root.winfo_pointerx()), float(self.root.winfo_pointery())
            self.active_monitor = monitor_for_point(self.monitors, x, y)
            active = f"Scherm {self.active_monitor.index}" if self.active_monitor else "buiten scherm"
            self.position_label.config(text=f"Muispositie: {active}    X: {int(x)}    Y: {int(y)}")
        except tk.TclError:
            pass

        if self.recorder.running:
            self.status.config(text=f"● Opnemen · {self.recorder.elapsed:.1f}s · {len(self.recorder.events):,} events", fg=RED)
        self.monitor_label.config(text=f"{len(self.monitors)} scherm(en)")
        self._redraw()
        self.root.after(30, self._tick)

    def _to_canvas(self, x: float, y: float) -> tuple[float, float]:
        left, top, width, height = self.bounds
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        margin = 28
        return (
            margin + (x - left) / max(1, width) * max(1, cw - margin * 2),
            margin + (y - top) / max(1, height) * max(1, ch - margin * 2),
        )

    def _redraw(self) -> None:
        self.canvas.delete("all")
        for monitor in self.monitors:
            x1, y1 = self._to_canvas(monitor.left, monitor.top)
            x2, y2 = self._to_canvas(monitor.right, monitor.bottom)
            active = self.active_monitor and monitor.index == self.active_monitor.index
            self.canvas.create_rectangle(x1, y1, x2, y2, fill="#102039" if active else "#091321",
                                         outline=CYAN if active else "#43516a", width=3 if active else 1)
            self.canvas.create_text((x1 + x2) / 2, y1 + 17, text=f"Scherm {monitor.index}",
                                    fill=TEXT if active else MUTED, font=("Segoe UI", 9, "bold"))
            self.canvas.create_text((x1 + x2) / 2, y1 + 35, text=f"{monitor.width} × {monitor.height}",
                                    fill=MUTED, font=("Segoe UI", 8))

        trace = list(self.live_trace)
        for a, b in zip(trace, trace[1:]):
            self.canvas.create_line(*self._to_canvas(a[1], a[2]), *self._to_canvas(b[1], b[2]),
                                    fill=PURPLE, width=2, smooth=True)
        try:
            px, py = float(self.root.winfo_pointerx()), float(self.root.winfo_pointery())
            cx, cy = self._to_canvas(px, py)
            self.canvas.create_oval(cx - 7, cy - 7, cx + 7, cy + 7, fill=CYAN, outline="#ffffff")
        except tk.TclError:
            pass

    def refresh_sessions(self, select_id: str | None = None) -> None:
        self.sessions = list_sessions()
        self.session_map = {session.session_id: session for session in self.sessions}
        for item in self.tree.get_children():
            self.tree.delete(item)
        for session in self.sessions:
            self.tree.insert("", "end", iid=session.session_id,
                             values=(session.created, session.label, f"{session.duration_s:.1f}s"))
        target = select_id or (self.sessions[0].session_id if self.sessions else None)
        if target and target in self.session_map:
            self.tree.selection_set(target)
            self.tree.focus(target)

    def start_recording(self) -> None:
        self.stop_replay()
        self.live_trace.clear()
        try:
            self.recorder.start()
        except Exception as exc:
            messagebox.showerror("AI Mouse", f"Recorder kon niet starten:\n{exc}")
            return
        self.record_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.play_btn.config(state="disabled")

    def stop_and_save(self) -> None:
        if not self.recorder.running:
            return
        events = self.recorder.stop()
        self.record_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.play_btn.config(state="normal")
        self.status.config(text="● Gereed", fg=GREEN)
        try:
            folder = save_global_recording(self.label_var.get(), events)
        except Exception as exc:
            messagebox.showerror("AI Mouse", str(exc))
            return
        self.refresh_sessions(folder.name)

    def play_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("AI Mouse", "Selecteer eerst een opname.")
            return
        session = self.session_map.get(selected[0])
        if session is None:
            return
        points = load_points(session.folder / "points.csv", max_points=2500)
        if len(points) < 2:
            messagebox.showwarning("AI Mouse", "Deze opname bevat te weinig bewegingen.")
            return
        self.stop_replay()
        self.replay_points = points
        self.replay_index = 0
        self.replay_started = time.perf_counter()
        self.live_trace.clear()
        self.status.config(text="● Replay", fg=PURPLE)
        self._replay_step()

    def _replay_step(self) -> None:
        if self.replay_index >= len(self.replay_points):
            self.stop_replay()
            return
        timestamp, x, y = self.replay_points[self.replay_index]
        self.live_trace.append((time.perf_counter(), x, y))
        self.active_monitor = monitor_for_point(self.monitors, x, y)
        delay = 12
        if self.replay_index + 1 < len(self.replay_points):
            delay = max(4, min(80, int((self.replay_points[self.replay_index + 1][0] - timestamp) * 1000)))
        self.replay_index += 1
        self.replay_after = self.root.after(delay, self._replay_step)

    def stop_replay(self) -> None:
        if self.replay_after:
            try:
                self.root.after_cancel(self.replay_after)
            except tk.TclError:
                pass
            self.replay_after = None
        if not self.recorder.running and hasattr(self, "status"):
            self.status.config(text="● Gereed", fg=GREEN)

    def open_recordings_folder(self) -> None:
        RECORDINGS.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(RECORDINGS.resolve()))
        except Exception as exc:
            messagebox.showerror("AI Mouse", f"Map kon niet openen:\n{exc}")

    def open_aim_lab(self) -> None:
        try:
            subprocess.Popen([sys.executable, "-m", "ai_mouse_hub.click_test"])
        except Exception as exc:
            messagebox.showerror("AI Mouse", f"Aim Lab kon niet openen:\n{exc}")

    def on_close(self) -> None:
        if self.recorder.running:
            self.recorder.stop()
        self.stop_replay()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
