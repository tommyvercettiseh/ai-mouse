from __future__ import annotations

import random
import threading
import time
import tkinter as tk
from collections import deque
from tkinter import messagebox, ttk

from .analysis import CleanPoint, clean_and_segment, segments
from .core import build_master_profile, generate_replay, list_sessions, load_master_profile, load_points
from .global_recorder import GlobalMouseRecorder, MouseEvent, save_global_recording, virtual_screen_bounds

BG = "#07111d"
PANEL = "#0d1928"
PANEL2 = "#142238"
TEXT = "#f4f7ff"
MUTED = "#8f9db2"
PURPLE = "#7b4dff"
BLUE = "#3478ff"
RED = "#ef4555"
GREEN = "#3ad37d"
BORDER = "#21334b"
TRACE = (126, 77, 255)


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AI Mouse")
        self.root.geometry("1180x760")
        self.root.minsize(900, 620)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.bounds = virtual_screen_bounds()
        self.recorder = GlobalMouseRecorder(on_event=self._queue_event)
        self.event_queue: deque[MouseEvent] = deque()
        self.live_trace: deque[tuple[float, float, float]] = deque(maxlen=900)
        self.sessions = []
        self.session_map = {}
        self.replay_segments: list[list[CleanPoint]] = []
        self.replay_segment_index = 0
        self.replay_point_index = 0
        self.replay_running = False
        self.replay_after: str | None = None
        self.replay_trace: deque[tuple[float, float, float]] = deque(maxlen=900)
        self.profile_mode = True

        self._styles()
        self._build()
        self.refresh_sessions()
        self._tick()

    def _styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=PANEL, foreground=TEXT, fieldbackground=PANEL, rowheight=30, bordercolor=BORDER)
        style.configure("Treeview.Heading", background=PANEL2, foreground=MUTED, bordercolor=BORDER)
        style.map("Treeview", background=[("selected", "#26385e")])
        style.configure("TCombobox", fieldbackground=PANEL2, background=PANEL2, foreground=TEXT)

    def _button(self, parent, text, command, bg=PANEL2, **kwargs):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=TEXT, activebackground=bg,
                         activeforeground=TEXT, relief="flat", cursor="hand2", font=("Segoe UI", 10, "bold"), **kwargs)

    def _build(self):
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True, padx=20, pady=18)

        header = tk.Frame(shell, bg=BG)
        header.pack(fill="x")
        tk.Label(header, text="AI Mouse", bg=BG, fg=TEXT, font=("Segoe UI", 24, "bold")).pack(side="left")
        self.status = tk.Label(header, text="● Klaar", bg=BG, fg=GREEN, font=("Segoe UI", 10, "bold"))
        self.status.pack(side="right")
        tk.Label(shell, text="Neem je muis op. Bekijk de fading trace. Speel je profiel lokaal terug.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 14))

        stage = tk.Frame(shell, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        stage.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(stage, bg="#050c15", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=12)
        self.canvas.bind("<Configure>", lambda _e: self._redraw())

        controls = tk.Frame(shell, bg=BG)
        controls.pack(fill="x", pady=(12, 10))
        self.record_btn = self._button(controls, "● Record", self.start_recording, bg=RED, padx=20, pady=10)
        self.record_btn.pack(side="left")
        self.pause_btn = self._button(controls, "Ⅱ Pauze", self.toggle_pause, padx=18, pady=10, state="disabled")
        self.pause_btn.pack(side="left", padx=8)
        self.save_btn = self._button(controls, "■ Opslaan", self.stop_and_save, bg=BLUE, padx=18, pady=10, state="disabled")
        self.save_btn.pack(side="left")
        self.replay_btn = self._button(controls, "▶ Replay profiel", self.toggle_replay, bg=PURPLE, padx=20, pady=10)
        self.replay_btn.pack(side="right")
        self.fade_var = tk.DoubleVar(value=2.5)
        tk.Label(controls, text="Trace", bg=BG, fg=MUTED).pack(side="right", padx=(0, 4))
        tk.Scale(controls, from_=0.5, to=6.0, resolution=0.5, orient="horizontal", variable=self.fade_var,
                 bg=BG, fg=TEXT, troughcolor=PANEL2, highlightthickness=0, length=130).pack(side="right", padx=(0, 16))

        bottom = tk.Frame(shell, bg=BG)
        bottom.pack(fill="x")
        left = tk.Frame(bottom, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        columns = ("created", "label", "duration")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", height=5, selectmode="browse")
        for key, title, width in (("created", "Opname", 210), ("label", "Label", 120), ("duration", "Duur", 80)):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="w" if key != "duration" else "center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.load_selected())

        right = tk.Frame(bottom, bg=PANEL, width=330, highlightbackground=BORDER, highlightthickness=1)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        tk.Label(right, text="Opname", bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(12, 6))
        self.label_var = tk.StringVar(value="Browsing")
        ttk.Combobox(right, textvariable=self.label_var,
                     values=("Browsing", "Gaming", "Werk", "Precision", "Relaxed", "Fatigued"),
                     state="normal").pack(fill="x", padx=14)
        self.info = tk.Label(right, text="Geen opname geselecteerd", bg=PANEL, fg=MUTED, justify="left", anchor="nw",
                             wraplength=295, font=("Segoe UI", 9))
        self.info.pack(fill="both", expand=True, padx=14, pady=12)
        self._button(right, "Profiel vernieuwen", self.build_profile, bg=PANEL2, pady=8).pack(fill="x", padx=14, pady=(0, 12))

    def _queue_event(self, event: MouseEvent):
        self.event_queue.append(event)

    def _tick(self):
        now = time.perf_counter()
        while self.event_queue:
            event = self.event_queue.popleft()
            if event.event_type == "move":
                self.live_trace.append((now, event.x, event.y))
        if self.recorder.running:
            state = "Gepauzeerd" if self.recorder.paused else "Opnemen"
            self.status.config(text=f"● {state} · {self.recorder.elapsed:.1f}s · {len(self.recorder.events):,} events",
                               fg=PURPLE if self.recorder.paused else RED)
        self._redraw()
        self.root.after(25, self._tick)

    def _to_canvas(self, x: float, y: float) -> tuple[float, float]:
        left, top, width, height = self.bounds
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        return ((x - left) / width * cw, (y - top) / height * ch)

    def _draw_trace(self, trace: deque[tuple[float, float, float]], now: float):
        fade = max(0.5, self.fade_var.get())
        active = [(t, x, y) for t, x, y in trace if now - t <= fade]
        trace.clear()
        trace.extend(active)
        if len(active) < 2:
            return
        for index in range(1, len(active)):
            t1, x1, y1 = active[index - 1]
            t2, x2, y2 = active[index]
            age = now - t2
            strength = max(0.08, 1.0 - age / fade)
            r, g, b = TRACE
            colour = f"#{int(r*strength):02x}{int(g*strength):02x}{int(b*strength):02x}"
            a = self._to_canvas(x1, y1)
            c = self._to_canvas(x2, y2)
            self.canvas.create_line(*a, *c, fill=colour, width=1 + 4 * strength, smooth=True)
        _, x, y = active[-1]
        cx, cy = self._to_canvas(x, y)
        self.canvas.create_oval(cx-8, cy-8, cx+8, cy+8, fill="#ae82ff", outline="#ffffff", width=2)

    def _redraw(self):
        self.canvas.delete("all")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.create_text(18, 16, text="LIVE TRACE" if self.recorder.running else "REPLAY",
                                fill=MUTED, anchor="nw", font=("Segoe UI", 9, "bold"))
        self.canvas.create_rectangle(1, 1, max(2, w-2), max(2, h-2), outline="#15253a")
        now = time.perf_counter()
        self._draw_trace(self.live_trace if self.recorder.running else self.replay_trace, now)

    def start_recording(self):
        self.stop_replay()
        self.live_trace.clear()
        try:
            self.recorder.start()
        except Exception as exc:
            messagebox.showerror("AI Mouse", f"Globale recorder kon niet starten:\n{exc}")
            return
        self.record_btn.config(state="disabled")
        self.pause_btn.config(state="normal", text="Ⅱ Pauze")
        self.save_btn.config(state="normal")

    def toggle_pause(self):
        if not self.recorder.running:
            return
        if self.recorder.paused:
            self.recorder.resume()
            self.pause_btn.config(text="Ⅱ Pauze")
        else:
            self.recorder.pause()
            self.pause_btn.config(text="▶ Hervat")

    def stop_and_save(self):
        events = self.recorder.stop()
        self.record_btn.config(state="normal")
        self.pause_btn.config(state="disabled", text="Ⅱ Pauze")
        self.save_btn.config(state="disabled")
        self.status.config(text="● Klaar", fg=GREEN)
        try:
            folder = save_global_recording(self.label_var.get(), events)
        except Exception as exc:
            messagebox.showerror("AI Mouse", str(exc))
            return
        self.refresh_sessions(select_id=folder.name)

    def refresh_sessions(self, select_id: str | None = None):
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

    def load_selected(self):
        session = self.selected_session()
        if session is None:
            return
        raw = load_points(session.folder / "points.csv", max_points=100000)
        clean, summary = clean_and_segment(raw)
        self.replay_segments = segments(clean)
        self.replay_segment_index = 0
        self.replay_point_index = 0
        self.info.config(text=(f"{session.label}\n{session.duration_s:.1f} seconden · {session.point_count:,} events\n\n"
                               f"{summary.segment_count} bewegingen\n{summary.warp_count} jumps veilig uitgesloten\n"
                               f"{summary.pause_count} pauzes\n{summary.median_interval_ms:.1f} ms sampling"))

    def _profile_segment(self, segment: list[CleanPoint]) -> list[CleanPoint]:
        if len(segment) < 2 or not load_master_profile():
            return segment
        min_x, max_x = min(p.x for p in segment), max(p.x for p in segment)
        min_y, max_y = min(p.y for p in segment), max(p.y for p in segment)
        width, height = max(1.0, max_x-min_x), max(1.0, max_y-min_y)
        normalized = [((p.x-min_x)/width, (p.y-min_y)/height) for p in segment]
        generated = generate_replay(normalized, random.Random(42 + self.replay_segment_index), strength=0.018)
        return [CleanPoint(p.timestamp, min_x+x*width, min_y+y*height, p.segment_id) for p, (x, y) in zip(segment, generated)]

    def toggle_replay(self):
        if self.replay_running:
            self.stop_replay()
            return
        if not self.replay_segments:
            self.load_selected()
        if not self.replay_segments:
            messagebox.showinfo("AI Mouse", "Neem eerst een sessie op of selecteer een bestaande opname.")
            return
        self.replay_running = True
        self.replay_btn.config(text="Ⅱ Pauze replay")
        self.status.config(text="● Profiel replay", fg=PURPLE)
        self._replay_step()

    def _replay_step(self):
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
            dt = point.timestamp - segment[self.replay_point_index-1].timestamp
            delay = max(4, min(80, int(dt * 1000)))
        self.replay_point_index += 1
        self.replay_after = self.root.after(delay, self._replay_step)

    def stop_replay(self):
        self.replay_running = False
        self.replay_btn.config(text="▶ Replay profiel")
        if self.replay_after:
            self.root.after_cancel(self.replay_after)
            self.replay_after = None
        if not self.recorder.running:
            self.status.config(text="● Klaar", fg=GREEN)

    def build_profile(self):
        try:
            profile = build_master_profile(list_sessions())
        except Exception as exc:
            messagebox.showerror("AI Mouse", str(exc))
            return
        messagebox.showinfo("AI Mouse", f"Profiel vernieuwd uit {profile['source_count']} opname(s).")

    def on_close(self):
        if self.recorder.running:
            self.recorder.stop()
        self.stop_replay()
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
