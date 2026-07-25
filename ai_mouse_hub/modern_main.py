from __future__ import annotations

import os
import random
import subprocess
import sys
import time
import tkinter as tk
from collections import deque
from tkinter import messagebox, ttk

from .analysis import CleanPoint, clean_and_segment, segments
from .core import RECORDINGS, build_master_profile, generate_replay, list_sessions, load_master_profile, load_points
from .global_recorder import GlobalMouseRecorder, MouseEvent, save_global_recording, virtual_screen_bounds
from .screen_layout import MonitorInfo, enumerate_monitors, monitor_for_point

BG = "#070b18"
PANEL = "#10162a"
PANEL_2 = "#151d36"
TEXT = "#f7f8ff"
MUTED = "#919ab5"
PURPLE = "#8a3ffc"
BLUE = "#2478ff"
CYAN = "#26d9ff"
RED = "#ff4d6d"
GREEN = "#3ee58a"
BORDER = "#263154"
TRACE = (123, 76, 255)


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AI Mouse Hub")
        self.root.geometry("1260x820")
        self.root.minsize(1000, 680)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.bounds = virtual_screen_bounds()
        self.monitors = enumerate_monitors()
        self.active_monitor: MonitorInfo | None = None
        self.recorder = GlobalMouseRecorder(on_event=self._queue_event)
        self.event_queue: deque[MouseEvent] = deque()
        self.live_trace: deque[tuple[float, float, float]] = deque(maxlen=1200)
        self.replay_trace: deque[tuple[float, float, float]] = deque(maxlen=1200)
        self.sessions = []
        self.session_map = {}
        self.replay_segments: list[list[CleanPoint]] = []
        self.replay_segment_index = 0
        self.replay_point_index = 0
        self.replay_running = False
        self.replay_after: str | None = None

        self._styles()
        self._build()
        self.refresh_sessions()
        self._refresh_profile_state()
        self._tick()

    def _styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=PANEL, foreground=TEXT, fieldbackground=PANEL, rowheight=34, bordercolor=BORDER)
        style.configure("Treeview.Heading", background=PANEL_2, foreground=MUTED, bordercolor=BORDER)
        style.map("Treeview", background=[("selected", "#2a2459")], foreground=[("selected", TEXT)])
        style.configure("TCombobox", fieldbackground=PANEL_2, background=PANEL_2, foreground=TEXT)

    def _button(self, parent, text, command, bg=PANEL_2, **kwargs):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=TEXT, activebackground=bg,
                         activeforeground=TEXT, disabledforeground="#64708c", relief="flat", bd=0,
                         cursor="hand2", font=("Segoe UI", 10, "bold"), **kwargs)

    def _build(self) -> None:
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True, padx=18, pady=16)

        hero = tk.Canvas(shell, height=84, bg=BG, highlightthickness=0)
        hero.pack(fill="x")
        hero.bind("<Configure>", lambda e: self._draw_hero(hero, e.width, e.height))

        actions = tk.Frame(shell, bg=BG)
        actions.pack(fill="x", pady=(12, 12))
        self.record_btn = self._button(actions, "●  Record", self.start_recording, bg=RED, padx=24, pady=11)
        self.record_btn.pack(side="left")
        self.pause_btn = self._button(actions, "Ⅱ  Pauze", self.toggle_pause, padx=22, pady=11, state="disabled")
        self.pause_btn.pack(side="left", padx=8)
        self.save_btn = self._button(actions, "■  Opslaan", self.stop_and_save, bg=BLUE, padx=22, pady=11, state="disabled")
        self.save_btn.pack(side="left")
        self._button(actions, "◎  Kliktest", self.open_click_test, bg="#213b84", padx=20, pady=11).pack(side="right")
        self.replay_btn = self._button(actions, "▶  Replay profiel", self.toggle_replay, bg=PURPLE, padx=22, pady=11)
        self.replay_btn.pack(side="right", padx=8)

        stage = tk.Frame(shell, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        stage.pack(fill="both", expand=True)
        top = tk.Frame(stage, bg=PANEL)
        top.pack(fill="x", padx=16, pady=(12, 7))
        tk.Label(top, text="Schermvisualisatie", bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(side="left")
        self.monitor_status = tk.Label(top, text=self._monitor_text(), bg=PANEL, fg=MUTED, font=("Segoe UI", 9))
        self.monitor_status.pack(side="left", padx=12)
        self.status = tk.Label(top, text="● Klaar", bg=PANEL, fg=GREEN, font=("Segoe UI", 9, "bold"))
        self.status.pack(side="right")
        self.fade_var = tk.DoubleVar(value=2.5)
        tk.Scale(top, from_=0.5, to=6.0, resolution=0.5, orient="horizontal", variable=self.fade_var,
                 bg=PANEL, fg=TEXT, troughcolor=BORDER, highlightthickness=0, length=125).pack(side="right", padx=(8, 16))
        tk.Label(top, text="Fade", bg=PANEL, fg=MUTED).pack(side="right")

        self.canvas = tk.Canvas(stage, bg="#060a15", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.canvas.bind("<Configure>", lambda _e: self._redraw())

        bottom = tk.Frame(shell, bg=BG)
        bottom.pack(fill="x", pady=(12, 0))
        recordings = tk.Frame(bottom, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        recordings.pack(side="left", fill="both", expand=True, padx=(0, 8))
        recording_header = tk.Frame(recordings, bg=PANEL)
        recording_header.pack(fill="x", padx=14, pady=(11, 6))
        tk.Label(recording_header, text="Opnames", bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(side="left")
        self._button(recording_header, "▣  Open opnamemap", self.open_recordings_folder, padx=12, pady=6).pack(side="right")

        columns = ("created", "label", "duration")
        self.tree = ttk.Treeview(recordings, columns=columns, show="headings", height=5, selectmode="browse")
        for key, title, width in (("created", "Opname", 220), ("label", "Label", 125), ("duration", "Duur", 85)):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="w" if key != "duration" else "center")
        self.tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.load_selected())

        profile = tk.Frame(bottom, bg="#11172e", width=355, highlightbackground="#46317c", highlightthickness=1)
        profile.pack(side="right", fill="y")
        profile.pack_propagate(False)
        tk.Label(profile, text="Jouw muisprofiel", bg="#11172e", fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
        self.profile_status = tk.Label(profile, text="Nog geen profiel", bg="#11172e", fg=MUTED, justify="left", anchor="nw", wraplength=315)
        self.profile_status.pack(fill="x", padx=16, pady=(0, 10))
        self.label_var = tk.StringVar(value="Browsing")
        ttk.Combobox(profile, textvariable=self.label_var,
                     values=("Browsing", "Gaming", "Werk", "Precision", "Relaxed", "Fatigued"),
                     state="normal").pack(fill="x", padx=16, pady=(0, 10))
        self.info = tk.Label(profile, text="Maak eerst een opname.", bg="#11172e", fg=MUTED, justify="left", anchor="nw", wraplength=315)
        self.info.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        self.profile_btn = self._button(profile, "✦  Masterprofiel maken", self.build_profile, bg=PURPLE, padx=14, pady=11)
        self.profile_btn.pack(fill="x", padx=16, pady=(0, 16))

    def _draw_hero(self, canvas: tk.Canvas, width: int, height: int) -> None:
        canvas.delete("all")
        start, end = (21, 16, 61), (10, 45, 103)
        for x in range(max(1, width)):
            t = x / max(1, width - 1)
            rgb = tuple(int(start[i] + (end[i] - start[i]) * t) for i in range(3))
            canvas.create_line(x, 0, x, height, fill=f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}")
        canvas.create_oval(width * .38, -100, width * .78, 170, fill="#6724cc", outline="")
        canvas.create_text(24, 20, text="AI Mouse Hub", fill=TEXT, anchor="nw", font=("Segoe UI", 24, "bold"))
        canvas.create_text(25, 55, text="Record. Bekijk je schermen. Bouw je profiel.", fill="#c8cbed", anchor="nw", font=("Segoe UI", 10))
        canvas.create_text(width - 24, 32, text="v0.6.0  •  lokaal", fill="#d9dcff", anchor="ne", font=("Segoe UI", 9, "bold"))

    def _monitor_text(self) -> str:
        suffix = f" · actief: scherm {self.active_monitor.index}" if self.active_monitor else ""
        return f"{len(self.monitors)} scherm(en) · virtueel {self.bounds[2]}×{self.bounds[3]}{suffix}"

    def _queue_event(self, event: MouseEvent) -> None:
        self.event_queue.append(event)

    def _tick(self) -> None:
        now = time.perf_counter()
        while self.event_queue:
            event = self.event_queue.popleft()
            if event.event_type == "move":
                self.live_trace.append((now, event.x, event.y))
                self.active_monitor = monitor_for_point(self.monitors, event.x, event.y)
        if self.recorder.running:
            state = "Gepauzeerd" if self.recorder.paused else "Opnemen"
            self.status.config(text=f"● {state} · {self.recorder.elapsed:.1f}s · {len(self.recorder.events):,} events",
                               fg=PURPLE if self.recorder.paused else RED)
        self.monitor_status.config(text=self._monitor_text())
        self._redraw()
        self.root.after(25, self._tick)

    def _to_canvas(self, x: float, y: float) -> tuple[float, float]:
        left, top, width, height = self.bounds
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        margin = 34
        usable_w, usable_h = max(1, cw - margin * 2), max(1, ch - margin * 2)
        return (margin + (x - left) / width * usable_w, margin + (y - top) / height * usable_h)

    def _draw_monitors(self) -> None:
        for monitor in self.monitors:
            x1, y1 = self._to_canvas(monitor.left, monitor.top)
            x2, y2 = self._to_canvas(monitor.right, monitor.bottom)
            active = self.active_monitor and monitor.index == self.active_monitor.index
            outline = CYAN if active else "#46516f"
            fill = "#101b39" if active else "#0a1020"
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=3 if active else 1)
            title = f"Scherm {monitor.index}{' · primair' if monitor.primary else ''}"
            self.canvas.create_text((x1+x2)/2, y1+17, text=title, fill=TEXT if active else MUTED, font=("Segoe UI", 9, "bold"))
            self.canvas.create_text((x1+x2)/2, y1+36, text=f"{monitor.width} × {monitor.height}", fill=MUTED, font=("Segoe UI", 8))

    def _draw_trace(self, trace: deque[tuple[float, float, float]], now: float) -> None:
        fade = max(.5, self.fade_var.get())
        active = [(t, x, y) for t, x, y in trace if now - t <= fade]
        trace.clear(); trace.extend(active)
        if not active:
            return
        for index in range(1, len(active)):
            _, x1, y1 = active[index - 1]
            t2, x2, y2 = active[index]
            strength = max(.08, 1 - (now - t2) / fade)
            r, g, b = TRACE
            colour = f"#{int(r*strength):02x}{int(g*strength):02x}{int(b*strength):02x}"
            self.canvas.create_line(*self._to_canvas(x1, y1), *self._to_canvas(x2, y2), fill=colour, width=1 + 5*strength, smooth=True)
        _, x, y = active[-1]
        cx, cy = self._to_canvas(x, y)
        self.canvas.create_oval(cx-12, cy-12, cx+12, cy+12, fill="#1b1640", outline="")
        self.canvas.create_oval(cx-7, cy-7, cx+7, cy+7, fill=CYAN, outline="#ffffff")

    def _redraw(self) -> None:
        self.canvas.delete("all")
        self._draw_monitors()
        self._draw_trace(self.live_trace if self.recorder.running else self.replay_trace, time.perf_counter())

    def start_recording(self) -> None:
        self.stop_replay(); self.live_trace.clear()
        try:
            self.recorder.start()
        except Exception as exc:
            messagebox.showerror("AI Mouse", f"Recorder kon niet starten:\n{exc}"); return
        self.record_btn.config(state="disabled")
        self.pause_btn.config(state="normal", text="Ⅱ  Pauze")
        self.save_btn.config(state="normal")

    def toggle_pause(self) -> None:
        if not self.recorder.running:
            return
        if self.recorder.paused:
            self.recorder.resume(); self.pause_btn.config(text="Ⅱ  Pauze")
        else:
            self.recorder.pause(); self.pause_btn.config(text="▶  Hervat")

    def stop_and_save(self) -> None:
        events = self.recorder.stop()
        self.record_btn.config(state="normal"); self.pause_btn.config(state="disabled", text="Ⅱ  Pauze"); self.save_btn.config(state="disabled")
        self.status.config(text="● Klaar", fg=GREEN)
        try:
            folder = save_global_recording(self.label_var.get(), events)
        except Exception as exc:
            messagebox.showerror("AI Mouse", str(exc)); return
        self.refresh_sessions(folder.name)
        self.info.config(text="Opname opgeslagen. Maak of vernieuw nu je masterprofiel.")

    def refresh_sessions(self, select_id: str | None = None) -> None:
        self.sessions = list_sessions(); self.session_map.clear()
        for item in self.tree.get_children(): self.tree.delete(item)
        target = None
        for session in self.sessions:
            item = self.tree.insert("", "end", values=(session.created, session.label, f"{session.duration_s:.1f}s"))
            self.session_map[item] = session
            if session.session_id == select_id: target = item
        if self.sessions and self.tree.get_children():
            chosen = target or self.tree.get_children()[0]
            self.tree.selection_set(chosen); self.tree.focus(chosen); self.load_selected()

    def selected_session(self):
        selected = self.tree.selection()
        return self.session_map.get(selected[0]) if selected else None

    def load_selected(self) -> None:
        session = self.selected_session()
        if not session: return
        clean, summary = clean_and_segment(load_points(session.folder / "points.csv", max_points=100000))
        self.replay_segments = segments(clean); self.replay_segment_index = 0; self.replay_point_index = 0
        self.info.config(text=f"{session.label}\n{session.duration_s:.1f} sec · {session.point_count:,} events\n\n{summary.segment_count} bewegingen\n{summary.warp_count} jumps gefilterd\n{summary.pause_count} pauzes")

    def _profile_segment(self, segment: list[CleanPoint]) -> list[CleanPoint]:
        if len(segment) < 2 or not load_master_profile(): return segment
        min_x, max_x = min(p.x for p in segment), max(p.x for p in segment)
        min_y, max_y = min(p.y for p in segment), max(p.y for p in segment)
        width, height = max(1., max_x-min_x), max(1., max_y-min_y)
        normalized = [((p.x-min_x)/width, (p.y-min_y)/height) for p in segment]
        generated = generate_replay(normalized, random.Random(42+self.replay_segment_index), strength=.018)
        return [CleanPoint(p.timestamp, min_x+x*width, min_y+y*height, p.segment_id) for p, (x, y) in zip(segment, generated)]

    def toggle_replay(self) -> None:
        if self.replay_running: self.stop_replay(); return
        if not load_master_profile(): messagebox.showinfo("AI Mouse", "Maak eerst een masterprofiel."); return
        if not self.replay_segments: self.load_selected()
        if not self.replay_segments: messagebox.showinfo("AI Mouse", "Selecteer eerst een opname."); return
        self.replay_running = True; self.replay_btn.config(text="Ⅱ  Pauze replay"); self.status.config(text="● Profiel replay", fg=PURPLE); self._replay_step()

    def _replay_step(self) -> None:
        if not self.replay_running: return
        if self.replay_segment_index >= len(self.replay_segments):
            self.replay_segment_index = 0; self.replay_point_index = 0; self.replay_trace.clear()
        segment = self._profile_segment(self.replay_segments[self.replay_segment_index])
        if self.replay_point_index >= len(segment):
            self.replay_segment_index += 1; self.replay_point_index = 0; self.replay_trace.clear(); self.replay_after = self.root.after(120, self._replay_step); return
        point = segment[self.replay_point_index]
        self.active_monitor = monitor_for_point(self.monitors, point.x, point.y)
        self.replay_trace.append((time.perf_counter(), point.x, point.y))
        delay = 16
        if self.replay_point_index > 0:
            delay = max(4, min(80, int((point.timestamp-segment[self.replay_point_index-1].timestamp)*1000)))
        self.replay_point_index += 1; self.replay_after = self.root.after(delay, self._replay_step)

    def stop_replay(self) -> None:
        self.replay_running = False; self.replay_btn.config(text="▶  Replay profiel")
        if self.replay_after:
            try: self.root.after_cancel(self.replay_after)
            except tk.TclError: pass
            self.replay_after = None
        if not self.recorder.running: self.status.config(text="● Klaar", fg=GREEN)

    def build_profile(self) -> None:
        sessions = list_sessions()
        if not sessions: messagebox.showinfo("AI Mouse", "Maak eerst minimaal één opname."); return
        try: profile = build_master_profile(sessions)
        except Exception as exc: messagebox.showerror("AI Mouse", str(exc)); return
        self._refresh_profile_state(); messagebox.showinfo("AI Mouse", f"Masterprofiel gemaakt uit {profile['source_count']} opname(s).")

    def _refresh_profile_state(self) -> None:
        profile = load_master_profile()
        if profile:
            self.profile_status.config(text=f"● Profiel actief\nGebouwd uit {profile.get('source_count', '?')} opname(s)", fg=GREEN)
            self.profile_btn.config(text="✦  Masterprofiel vernieuwen")
        else:
            self.profile_status.config(text="Nog geen actief profiel.\nMaak eerst een opname.", fg=MUTED)
            self.profile_btn.config(text="✦  Masterprofiel maken")

    def open_recordings_folder(self) -> None:
        RECORDINGS.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(RECORDINGS.resolve()))
        except Exception as exc:
            messagebox.showerror("AI Mouse", f"Opnamemap kon niet openen:\n{exc}")

    def open_click_test(self) -> None:
        if not load_master_profile(): messagebox.showinfo("AI Mouse", "Maak eerst een masterprofiel."); return
        try: subprocess.Popen([sys.executable, "-m", "ai_mouse_hub.click_test"])
        except Exception as exc: messagebox.showerror("AI Mouse", f"Kliktest kon niet openen:\n{exc}")

    def on_close(self) -> None:
        if self.recorder.running: self.recorder.stop()
        self.stop_replay(); self.root.destroy()


def main() -> None:
    root = tk.Tk(); App(root); root.mainloop()


if __name__ == "__main__":
    main()
