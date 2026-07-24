from __future__ import annotations

import random
import subprocess
import sys
import time
import tkinter as tk
from collections import deque
from tkinter import messagebox, ttk

from .analysis import CleanPoint, clean_and_segment, segments
from .core import build_master_profile, generate_replay, list_sessions, load_master_profile, load_points
from .global_recorder import GlobalMouseRecorder, MouseEvent, save_global_recording, virtual_screen_bounds

BG = "#070b18"
BG2 = "#0d1230"
PANEL = "#10162a"
PANEL_HOVER = "#171f3b"
TEXT = "#f7f8ff"
MUTED = "#8f98b3"
PURPLE = "#8a3ffc"
PINK = "#ef3fa9"
BLUE = "#2478ff"
CYAN = "#26d9ff"
RED = "#ff4d6d"
GREEN = "#3ee58a"
BORDER = "#252f52"
TRACE = (123, 76, 255)


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AI Mouse Hub")
        self.root.geometry("1220x790")
        self.root.minsize(980, 670)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.bounds = virtual_screen_bounds()
        self.recorder = GlobalMouseRecorder(on_event=self._queue_event)
        self.event_queue: deque[MouseEvent] = deque()
        self.live_trace: deque[tuple[float, float, float]] = deque(maxlen=1000)
        self.sessions = []
        self.session_map = {}
        self.replay_segments: list[list[CleanPoint]] = []
        self.replay_segment_index = 0
        self.replay_point_index = 0
        self.replay_running = False
        self.replay_after: str | None = None
        self.replay_trace: deque[tuple[float, float, float]] = deque(maxlen=1000)

        self._styles()
        self._build()
        self.refresh_sessions()
        self._refresh_profile_state()
        self._tick()

    def _styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=PANEL,
            foreground=TEXT,
            fieldbackground=PANEL,
            rowheight=34,
            bordercolor=BORDER,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Treeview.Heading",
            background="#151d36",
            foreground=MUTED,
            bordercolor=BORDER,
            font=("Segoe UI", 9, "bold"),
        )
        style.map("Treeview", background=[("selected", "#2a2459")], foreground=[("selected", TEXT)])
        style.configure("TCombobox", fieldbackground="#151d36", background="#151d36", foreground=TEXT)

    def _button(self, parent, text, command, bg=PANEL_HOVER, fg=TEXT, **kwargs):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=bg,
            activeforeground=fg,
            disabledforeground="#65708e",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            **kwargs,
        )

    def _gradient(self, canvas: tk.Canvas, width: int, height: int, start: str, end: str) -> None:
        width = max(1, width)
        height = max(1, height)
        s = tuple(int(start[i:i + 2], 16) for i in (1, 3, 5))
        e = tuple(int(end[i:i + 2], 16) for i in (1, 3, 5))
        for x in range(width):
            t = x / max(1, width - 1)
            rgb = tuple(int(s[j] + (e[j] - s[j]) * t) for j in range(3))
            colour = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            canvas.create_line(x, 0, x, height, fill=colour)

    def _build(self) -> None:
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True, padx=18, pady=16)

        hero = tk.Canvas(shell, height=88, bg=BG, highlightthickness=0)
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
        stage_top = tk.Frame(stage, bg=PANEL)
        stage_top.pack(fill="x", padx=16, pady=(12, 6))
        tk.Label(stage_top, text="Mouse trace", bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(side="left")
        self.status = tk.Label(stage_top, text="● Klaar", bg=PANEL, fg=GREEN, font=("Segoe UI", 9, "bold"))
        self.status.pack(side="right")
        self.fade_var = tk.DoubleVar(value=2.5)
        tk.Scale(
            stage_top,
            from_=0.5,
            to=6.0,
            resolution=0.5,
            orient="horizontal",
            variable=self.fade_var,
            bg=PANEL,
            fg=TEXT,
            troughcolor="#252f52",
            highlightthickness=0,
            length=125,
        ).pack(side="right", padx=(8, 16))
        tk.Label(stage_top, text="Fade", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(side="right")

        self.canvas = tk.Canvas(stage, bg="#060a15", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.canvas.bind("<Configure>", lambda _e: self._redraw())

        bottom = tk.Frame(shell, bg=BG)
        bottom.pack(fill="x", pady=(12, 0))

        recordings = tk.Frame(bottom, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        recordings.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(recordings, text="Opnames", bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(12, 6))
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
        self.profile_status = tk.Label(profile, text="Nog geen profiel", bg="#11172e", fg=MUTED, justify="left", anchor="nw", wraplength=315, font=("Segoe UI", 9))
        self.profile_status.pack(fill="x", padx=16, pady=(0, 10))

        self.label_var = tk.StringVar(value="Browsing")
        ttk.Combobox(
            profile,
            textvariable=self.label_var,
            values=("Browsing", "Gaming", "Werk", "Precision", "Relaxed", "Fatigued"),
            state="normal",
        ).pack(fill="x", padx=16, pady=(0, 10))

        self.info = tk.Label(profile, text="Maak eerst een opname.", bg="#11172e", fg=MUTED, justify="left", anchor="nw", wraplength=315, font=("Segoe UI", 9))
        self.info.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        self.profile_btn = self._button(profile, "✦  Masterprofiel maken", self.build_profile, bg=PURPLE, padx=14, pady=11)
        self.profile_btn.pack(fill="x", padx=16, pady=(0, 16))

    def _draw_hero(self, canvas: tk.Canvas, width: int, height: int) -> None:
        canvas.delete("all")
        self._gradient(canvas, width, height, "#15103d", "#0a2d67")
        canvas.create_oval(width * 0.35, -100, width * 0.75, 180, fill="#6b24d7", outline="")
        canvas.create_text(24, 22, text="AI Mouse Hub", fill=TEXT, anchor="nw", font=("Segoe UI", 24, "bold"))
        canvas.create_text(25, 57, text="Record. Opslaan. Profiel bouwen. Testen.", fill="#c8cbed", anchor="nw", font=("Segoe UI", 10))
        canvas.create_text(width - 24, 34, text="v0.5.0  •  lokaal", fill="#d9dcff", anchor="ne", font=("Segoe UI", 9, "bold"))

    def _queue_event(self, event: MouseEvent) -> None:
        self.event_queue.append(event)

    def _tick(self) -> None:
        now = time.perf_counter()
        while self.event_queue:
            event = self.event_queue.popleft()
            if event.event_type == "move":
                self.live_trace.append((now, event.x, event.y))
        if self.recorder.running:
            state = "Gepauzeerd" if self.recorder.paused else "Opnemen"
            self.status.config(text=f"● {state} · {self.recorder.elapsed:.1f}s · {len(self.recorder.events):,} events", fg=PURPLE if self.recorder.paused else RED)
        self._redraw()
        self.root.after(25, self._tick)

    def _to_canvas(self, x: float, y: float) -> tuple[float, float]:
        left, top, width, height = self.bounds
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        return ((x - left) / width * cw, (y - top) / height * ch)

    def _draw_trace(self, trace: deque[tuple[float, float, float]], now: float) -> None:
        fade = max(0.5, self.fade_var.get())
        active = [(t, x, y) for t, x, y in trace if now - t <= fade]
        trace.clear()
        trace.extend(active)
        if len(active) < 2:
            return
        for index in range(1, len(active)):
            _, x1, y1 = active[index - 1]
            t2, x2, y2 = active[index]
            strength = max(0.08, 1.0 - (now - t2) / fade)
            r, g, b = TRACE
            colour = f"#{int(r * strength):02x}{int(g * strength):02x}{int(b * strength):02x}"
            a = self._to_canvas(x1, y1)
            c = self._to_canvas(x2, y2)
            self.canvas.create_line(*a, *c, fill=colour, width=1 + 5 * strength, smooth=True)
        _, x, y = active[-1]
        cx, cy = self._to_canvas(x, y)
        self.canvas.create_oval(cx - 12, cy - 12, cx + 12, cy + 12, fill="#1b1640", outline="")
        self.canvas.create_oval(cx - 7, cy - 7, cx + 7, cy + 7, fill=CYAN, outline="#ffffff", width=1)

    def _redraw(self) -> None:
        self.canvas.delete("all")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        for x in range(0, w, 42):
            self.canvas.create_line(x, 0, x, h, fill="#0d1426")
        for y in range(0, h, 42):
            self.canvas.create_line(0, y, w, y, fill="#0d1426")
        self.canvas.create_text(18, 16, text="LIVE" if self.recorder.running else "REPLAY", fill=MUTED, anchor="nw", font=("Segoe UI", 9, "bold"))
        self._draw_trace(self.live_trace if self.recorder.running else self.replay_trace, time.perf_counter())

    def start_recording(self) -> None:
        self.stop_replay()
        self.live_trace.clear()
        try:
            self.recorder.start()
        except Exception as exc:
            messagebox.showerror("AI Mouse", f"Globale recorder kon niet starten:\n{exc}")
            return
        self.record_btn.config(state="disabled")
        self.pause_btn.config(state="normal", text="Ⅱ  Pauze")
        self.save_btn.config(state="normal")

    def toggle_pause(self) -> None:
        if not self.recorder.running:
            return
        if self.recorder.paused:
            self.recorder.resume()
            self.pause_btn.config(text="Ⅱ  Pauze")
        else:
            self.recorder.pause()
            self.pause_btn.config(text="▶  Hervat")

    def stop_and_save(self) -> None:
        events = self.recorder.stop()
        self.record_btn.config(state="normal")
        self.pause_btn.config(state="disabled", text="Ⅱ  Pauze")
        self.save_btn.config(state="disabled")
        self.status.config(text="● Klaar", fg=GREEN)
        try:
            folder = save_global_recording(self.label_var.get(), events)
        except Exception as exc:
            messagebox.showerror("AI Mouse", str(exc))
            return
        self.refresh_sessions(select_id=folder.name)
        self.info.config(text="Opname opgeslagen. Klik hieronder op Masterprofiel maken.")

    def refresh_sessions(self, select_id: str | None = None) -> None:
        self.sessions = list_sessions()
        self.session_map.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        target = None
        for session in self.sessions:
            item = self.tree.insert("", "end", values=(session.created, session.label, f"{session.duration_s:.1f}s"))
            self.session_map[item] = session
            if select_id == session.session_id:
                target = item
        if target or (self.sessions and self.tree.get_children()):
            chosen = target or self.tree.get_children()[0]
            self.tree.selection_set(chosen)
            self.tree.focus(chosen)
            self.load_selected()

    def selected_session(self):
        selected = self.tree.selection()
        return self.session_map.get(selected[0]) if selected else None

    def load_selected(self) -> None:
        session = self.selected_session()
        if session is None:
            return
        raw = load_points(session.folder / "points.csv", max_points=100000)
        clean, summary = clean_and_segment(raw)
        self.replay_segments = segments(clean)
        self.replay_segment_index = 0
        self.replay_point_index = 0
        self.info.config(text=(f"{session.label}\n{session.duration_s:.1f} sec · {session.point_count:,} events\n\n"
                               f"{summary.segment_count} bewegingen\n{summary.warp_count} jumps gefilterd\n"
                               f"{summary.pause_count} pauzes"))

    def _profile_segment(self, segment: list[CleanPoint]) -> list[CleanPoint]:
        if len(segment) < 2 or not load_master_profile():
            return segment
        min_x, max_x = min(p.x for p in segment), max(p.x for p in segment)
        min_y, max_y = min(p.y for p in segment), max(p.y for p in segment)
        width, height = max(1.0, max_x - min_x), max(1.0, max_y - min_y)
        normalized = [((p.x - min_x) / width, (p.y - min_y) / height) for p in segment]
        generated = generate_replay(normalized, random.Random(42 + self.replay_segment_index), strength=0.018)
        return [CleanPoint(p.timestamp, min_x + x * width, min_y + y * height, p.segment_id) for p, (x, y) in zip(segment, generated)]

    def toggle_replay(self) -> None:
        if self.replay_running:
            self.stop_replay()
            return
        if not load_master_profile():
            messagebox.showinfo("AI Mouse", "Maak eerst een masterprofiel met de paarse knop rechtsonder.")
            return
        if not self.replay_segments:
            self.load_selected()
        if not self.replay_segments:
            messagebox.showinfo("AI Mouse", "Neem eerst een sessie op of selecteer een bestaande opname.")
            return
        self.replay_running = True
        self.replay_btn.config(text="Ⅱ  Pauze replay")
        self.status.config(text="● Profiel replay", fg=PURPLE)
        self._replay_step()

    def _replay_step(self) -> None:
        if not self.replay_running:
            return
        if self.replay_segment_index >= len(self.replay_segments):
            self.replay_segment_index = 0
            self.replay_point_index = 0
            self.replay_trace.clear()
        source = self.replay_segments[self.replay_segment_index]
        segment = self._profile_segment(source)
        if self.replay_point_index >= len(segment):
            self.replay_segment_index += 1
            self.replay_point_index = 0
            self.replay_trace.clear()
            self.replay_after = self.root.after(120, self._replay_step)
            return
        point = segment[self.replay_point_index]
        self.replay_trace.append((time.perf_counter(), point.x, point.y))
        delay = 16
        if self.replay_point_index > 0:
            dt = point.timestamp - segment[self.replay_point_index - 1].timestamp
            delay = max(4, min(80, int(dt * 1000)))
        self.replay_point_index += 1
        self.replay_after = self.root.after(delay, self._replay_step)

    def stop_replay(self) -> None:
        self.replay_running = False
        self.replay_btn.config(text="▶  Replay profiel")
        if self.replay_after:
            try:
                self.root.after_cancel(self.replay_after)
            except tk.TclError:
                pass
            self.replay_after = None
        if not self.recorder.running:
            self.status.config(text="● Klaar", fg=GREEN)

    def build_profile(self) -> None:
        sessions = list_sessions()
        if not sessions:
            messagebox.showinfo("AI Mouse", "Maak eerst minimaal één opname en sla die op.")
            return
        try:
            profile = build_master_profile(sessions)
        except Exception as exc:
            messagebox.showerror("AI Mouse", str(exc))
            return
        self._refresh_profile_state()
        messagebox.showinfo("AI Mouse", f"Masterprofiel gemaakt uit {profile['source_count']} opname(s).")

    def _refresh_profile_state(self) -> None:
        profile = load_master_profile()
        if profile:
            count = profile.get("source_count", "?")
            self.profile_status.config(text=f"● Profiel actief\nGebouwd uit {count} opname(s)", fg=GREEN)
            self.profile_btn.config(text="✦  Masterprofiel vernieuwen")
        else:
            self.profile_status.config(text="Nog geen actief profiel.\nMaak eerst een opname en bouw daarna je profiel.", fg=MUTED)
            self.profile_btn.config(text="✦  Masterprofiel maken")

    def open_click_test(self) -> None:
        if not load_master_profile():
            messagebox.showinfo("AI Mouse", "Maak eerst een masterprofiel met de paarse knop rechtsonder.")
            return
        try:
            subprocess.Popen([sys.executable, "-m", "ai_mouse_hub.click_test"])
        except Exception as exc:
            messagebox.showerror("AI Mouse", f"Kliktest kon niet openen:\n{exc}")

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
