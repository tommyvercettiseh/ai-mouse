from __future__ import annotations

import random
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from .core import (
    build_master_profile,
    generate_replay,
    list_sessions,
    load_master_profile,
    load_points,
    normalize_path,
    run_stress_test,
    set_included,
    similarity,
)
from .global_recorder import GlobalMouseRecorder, MouseEvent, save_global_recording, virtual_screen_bounds

BG = "#06101d"
SIDEBAR = "#081421"
PANEL = "#0d1928"
PANEL2 = "#111f31"
TEXT = "#f5f7ff"
MUTED = "#8d9bb0"
BLUE = "#3478ff"
PURPLE = "#7b4dff"
PURPLE2 = "#a269ff"
RED = "#ef3f4f"
GREEN = "#37d27c"
CYAN = "#18bfff"
BORDER = "#20324a"


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AI Mouse – Global Tracking & Fading Replay")
        self.root.geometry("1540x920")
        self.root.minsize(1180, 760)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.recorder = GlobalMouseRecorder(on_event=self._queue_live_event)
        self.live_queue: list[MouseEvent] = []
        self.live_lock = threading.Lock()
        self.sessions = []
        self.session_by_item = {}
        self.replay_points: list[tuple[float, float, float]] = []
        self.replay_index = 0
        self.replay_running = False
        self.replay_after: str | None = None
        self.replay_segments: list[int] = []
        self.virtual_bounds = virtual_screen_bounds()

        self._styles()
        self._build()
        self.refresh()
        self._pump_live_events()

    def _styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=PANEL, foreground=TEXT, fieldbackground=PANEL, bordercolor=BORDER, rowheight=31, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background=PANEL2, foreground=MUTED, bordercolor=BORDER, font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#1d3563")])
        style.configure("TCombobox", fieldbackground=PANEL2, background=PANEL2, foreground=TEXT)

    def button(self, parent, text, command, bg=PANEL2, fg=TEXT, **kwargs):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground=bg, activeforeground=fg, relief="flat", cursor="hand2", font=("Segoe UI", 9, "bold"), **kwargs)

    def _build(self):
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True)
        self._build_sidebar(shell)
        content = tk.Frame(shell, bg=BG)
        content.pack(side="left", fill="both", expand=True, padx=18, pady=16)
        self._build_header(content)
        self._build_replay_stage(content)
        self._build_controls(content)
        self._build_bottom(content)

    def _build_sidebar(self, parent):
        bar = tk.Frame(parent, bg=SIDEBAR, width=235, highlightbackground="#14253a", highlightthickness=1)
        bar.pack(side="left", fill="y")
        bar.pack_propagate(False)
        tk.Label(bar, text="◔  AI Mouse", bg=SIDEBAR, fg=TEXT, font=("Segoe UI", 19, "bold")).pack(anchor="w", padx=25, pady=(24, 30))
        items = (("⌂", "Dashboard"), ("◉", "Live Tracking"), ("▣", "Opnames"), ("◎", "Profielen"), ("▷", "Replay"), ("△", "Stress Lab"), ("⚙", "Instellingen"), ("≡", "Logs"))
        for icon, label in items:
            active = label == "Replay"
            row = tk.Frame(bar, bg="#152654" if active else SIDEBAR, highlightbackground=PURPLE if active else SIDEBAR, highlightthickness=1 if active else 0)
            row.pack(fill="x", padx=14, pady=3)
            tk.Label(row, text=f"{icon}   {label}", bg=row["bg"], fg=TEXT if active else "#b6c0cf", font=("Segoe UI", 10, "bold" if active else "normal"), anchor="w", padx=12, pady=11).pack(fill="x")
        tk.Frame(bar, bg=SIDEBAR).pack(fill="both", expand=True)
        status = tk.Frame(bar, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        status.pack(fill="x", padx=16, pady=(0, 12))
        tk.Label(status, text="Systeemstatus", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(12, 4))
        self.system_status = tk.Label(status, text="● Alles draait soepel", bg=PANEL, fg=GREEN, font=("Segoe UI", 9))
        self.system_status.pack(anchor="w", padx=14, pady=(0, 12))
        tk.Label(bar, text="AI Mouse v0.2.0\n100% lokaal · geen toetsenborddata", bg=SIDEBAR, fg=MUTED, justify="left", font=("Segoe UI", 8)).pack(anchor="w", padx=24, pady=(0, 20))

    def _build_header(self, parent):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x")
        left = tk.Frame(row, bg=BG)
        left.pack(side="left")
        tk.Label(left, text="Live Simulatie & Fading Trace", bg=BG, fg=TEXT, font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(left, text="Globale muisregistratie over al je schermen en applicaties.", bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))
        privacy = tk.Frame(row, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        privacy.pack(side="right", padx=(10, 0))
        tk.Label(privacy, text="◈  Volledig lokaal", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16, pady=(10, 2))
        tk.Label(privacy, text="Geen cloud. Geen sync. Geen toetsen.", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=16, pady=(0, 10))
        live = tk.Frame(row, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        live.pack(side="right")
        self.record_badge = tk.Label(live, text="● Opname gestopt", bg=PANEL, fg=MUTED, font=("Segoe UI", 10, "bold"))
        self.record_badge.pack(anchor="w", padx=16, pady=(10, 2))
        self.record_timer = tk.Label(live, text="Klaar om te volgen", bg=PANEL, fg=MUTED, font=("Segoe UI", 8))
        self.record_timer.pack(anchor="w", padx=16, pady=(0, 10))

    def _build_replay_stage(self, parent):
        stage = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        stage.pack(fill="both", expand=True, pady=(14, 10))
        top = tk.Frame(stage, bg=PANEL)
        top.pack(fill="x", padx=14, pady=(11, 8))
        tk.Label(top, text="▣  Simulatie – volledige virtuele desktop", bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(side="left")
        self.screen_label = tk.Label(top, text=self._bounds_text(), bg=PANEL, fg=MUTED, font=("Segoe UI", 9))
        self.screen_label.pack(side="right")
        self.replay_canvas = tk.Canvas(stage, bg="#050c16", highlightbackground=BORDER, highlightthickness=1)
        self.replay_canvas.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.replay_canvas.bind("<Configure>", lambda _e: self._draw_screen_grid())

    def _build_controls(self, parent):
        box = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        box.pack(fill="x", pady=(0, 10))
        controls = tk.Frame(box, bg=PANEL)
        controls.pack(fill="x", padx=14, pady=(11, 7))
        self.record_btn = self.button(controls, "● Start globale opname", self.start_recording, bg=RED, padx=16, pady=9)
        self.record_btn.pack(side="left")
        self.stop_btn = self.button(controls, "■ Stop & opslaan", self.stop_recording, bg=BLUE, padx=16, pady=9, state="disabled")
        self.stop_btn.pack(side="left", padx=(8, 18))
        self.play_btn = self.button(controls, "▶ Replay", self.toggle_replay, bg=PURPLE, padx=18, pady=9)
        self.play_btn.pack(side="left")
        self.button(controls, "↺ Opnieuw", self.restart_replay, padx=14, pady=9).pack(side="left", padx=(8, 18))
        tk.Label(controls, text="Snelheid", bg=PANEL, fg=MUTED).pack(side="left")
        self.speed_var = tk.DoubleVar(value=1.0)
        tk.Scale(controls, from_=0.25, to=4.0, resolution=0.25, orient="horizontal", variable=self.speed_var, bg=PANEL, fg=TEXT, troughcolor="#25334a", highlightthickness=0, length=130).pack(side="left", padx=(6, 16))
        tk.Label(controls, text="Fading", bg=PANEL, fg=MUTED).pack(side="left")
        self.fade_var = tk.DoubleVar(value=3.0)
        tk.Scale(controls, from_=0.5, to=8.0, resolution=0.5, orient="horizontal", variable=self.fade_var, bg=PANEL, fg=TEXT, troughcolor="#25334a", highlightthickness=0, length=130).pack(side="left", padx=(6, 0))
        self.progress = tk.Canvas(box, bg=PANEL, height=24, highlightthickness=0)
        self.progress.pack(fill="x", padx=16, pady=(0, 8))

    def _build_bottom(self, parent):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x")
        row.grid_columnconfigure(0, weight=6)
        row.grid_columnconfigure(1, weight=4)
        sessions = tk.Frame(row, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        sessions.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tk.Label(sessions, text="Opnames", bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(10, 6))
        columns = ("created", "label", "duration", "points", "included")
        self.tree = ttk.Treeview(sessions, columns=columns, show="headings", height=5, selectmode="browse")
        for col, title, width in (("created", "Datum", 175), ("label", "Label", 110), ("duration", "Duur", 75), ("points", "Events", 70), ("included", "Profiel", 65)):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="center" if col != "created" else "w")
        self.tree.pack(fill="both", expand=True, padx=14)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.load_selected_replay())
        foot = tk.Frame(sessions, bg=PANEL)
        foot.pack(fill="x", padx=14, pady=9)
        self.label_var = tk.StringVar(value="Browsing")
        ttk.Combobox(foot, textvariable=self.label_var, values=("Browsing", "Gaming", "Werk", "Precision", "Relaxed", "Fatigued"), state="normal", width=18).pack(side="left")
        self.button(foot, "Toggle profiel", self.toggle_selected, padx=10, pady=5).pack(side="right")

        stats = tk.Frame(row, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        stats.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        tk.Label(stats, text="Sessie & profiel", bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(10, 8))
        self.stats_text = tk.Label(stats, text="Selecteer een opname", bg=PANEL, fg=MUTED, justify="left", anchor="nw", font=("Segoe UI", 9))
        self.stats_text.pack(fill="both", expand=True, padx=14)
        actions = tk.Frame(stats, bg=PANEL)
        actions.pack(fill="x", padx=14, pady=10)
        self.button(actions, "Profiel bouwen", self.build_profile_async, bg=BLUE, padx=12, pady=7).pack(side="left")
        self.button(actions, "100× Stress Lab", self.run_stress_async, bg=PURPLE, padx=12, pady=7).pack(side="right")

    def _bounds_text(self) -> str:
        left, top, width, height = self.virtual_bounds
        return f"Virtueel scherm: {width}×{height} vanaf ({left}, {top})"

    def _queue_live_event(self, event: MouseEvent):
        with self.live_lock:
            self.live_queue.append(event)

    def _pump_live_events(self):
        queued: list[MouseEvent] = []
        with self.live_lock:
            if self.live_queue:
                queued = self.live_queue[:]
                self.live_queue.clear()
        for event in queued:
            if event.event_type == "move":
                self._draw_live_point(event)
        if self.recorder.running:
            elapsed = time.perf_counter() - self.recorder.started_at
            self.record_timer.config(text=f"Actief: {elapsed:0.1f}s · {len(self.recorder.events):,} events")
        self.root.after(30, self._pump_live_events)

    def start_recording(self):
        self.virtual_bounds = virtual_screen_bounds()
        self.screen_label.config(text=self._bounds_text())
        self._clear_trace()
        self.recorder.start()
        self.record_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.record_badge.config(text="● Opname actief", fg=GREEN)
        self.system_status.config(text="● Globale tracking actief", fg=GREEN)

    def stop_recording(self):
        events = self.recorder.stop()
        self.record_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.record_badge.config(text="● Opname gestopt", fg=MUTED)
        self.system_status.config(text="● Alles draait soepel", fg=GREEN)
        try:
            folder = save_global_recording(self.label_var.get(), events)
        except Exception as exc:
            messagebox.showwarning("Opname", str(exc))
            return
        self.record_timer.config(text=f"Opgeslagen: {folder.name}")
        self.refresh(select_session=folder.name)

    def _map_point(self, x: float, y: float) -> tuple[float, float]:
        left, top, width, height = self.virtual_bounds
        cw = max(100, self.replay_canvas.winfo_width())
        ch = max(100, self.replay_canvas.winfo_height())
        pad = 24
        return (pad + ((x - left) / width) * (cw - 2 * pad), pad + ((y - top) / height) * (ch - 2 * pad))

    def _draw_screen_grid(self):
        self.replay_canvas.delete("grid")
        w = max(100, self.replay_canvas.winfo_width())
        h = max(100, self.replay_canvas.winfo_height())
        self.replay_canvas.create_rectangle(20, 20, w - 20, h - 20, outline="#243652", width=2, tags="grid")
        self.replay_canvas.create_text(34, 34, text="LIVE / REPLAY · volledige desktop", fill=MUTED, anchor="nw", font=("Segoe UI", 9, "bold"), tags="grid")

    def _draw_live_point(self, event: MouseEvent):
        x, y = self._map_point(event.x, event.y)
        if hasattr(self, "last_live_xy") and self.last_live_xy:
            x1, y1 = self.last_live_xy
            item = self.replay_canvas.create_line(x1, y1, x, y, fill=PURPLE2, width=3, smooth=True, tags="trace")
            self.replay_segments.append(item)
            self.root.after(int(self.fade_var.get() * 1000), lambda i=item: self._fade_item(i, 0))
        self.last_live_xy = (x, y)
        self.replay_canvas.delete("cursor")
        self.replay_canvas.create_oval(x - 9, y - 9, x + 9, y + 9, fill=PURPLE, outline="#d7c9ff", width=2, tags="cursor")

    def _fade_item(self, item: int, step: int):
        colors = ("#8f64ff", "#694bd1", "#4c379a", "#33296a", "#211d45", "#111828")
        try:
            if step >= len(colors):
                self.replay_canvas.delete(item)
                return
            self.replay_canvas.itemconfig(item, fill=colors[step])
            self.root.after(90, lambda: self._fade_item(item, step + 1))
        except tk.TclError:
            return

    def _clear_trace(self):
        self.pause_replay()
        self.replay_canvas.delete("trace")
        self.replay_canvas.delete("cursor")
        self.replay_segments.clear()
        self.last_live_xy = None
        self.replay_index = 0
        self._draw_screen_grid()
        self._draw_progress()

    def refresh(self, select_session: str | None = None):
        self.sessions = list_sessions()
        self.session_by_item.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        target = None
        for session in self.sessions:
            item = self.tree.insert("", "end", values=(session.created, session.label, f"{session.duration_s:.1f}s", session.point_count, "Ja" if session.included else "Nee"))
            self.session_by_item[item] = session
            if select_session and session.session_id == select_session:
                target = item
        if target:
            self.tree.selection_set(target)
            self.tree.see(target)
            self.load_selected_replay()
        profile = load_master_profile()
        if profile:
            self.stats_text.config(text=f"Profielversie: {profile.get('profile_version')}\nBronnen: {profile.get('source_count')}\nLabels: {', '.join(profile.get('labels') or [])}\n\nSelecteer een sessie voor fading replay.")

    def selected(self):
        selection = self.tree.selection()
        return self.session_by_item.get(selection[0]) if selection else None

    def toggle_selected(self):
        session = self.selected()
        if session:
            set_included(session, not session.included)
            self.refresh(select_session=session.session_id)

    def load_selected_replay(self):
        session = self.selected()
        if session is None:
            return
        points = load_points(session.folder / "points.csv", max_points=20000)
        self.replay_points = points
        self.virtual_bounds = self._bounds_from_points(points)
        self._clear_trace()
        normalized = normalize_path(points)
        generated = generate_replay(normalized, random.Random(42)) if normalized else []
        score = similarity(normalized, generated) if normalized else 0.0
        self.stats_text.config(text=f"Label: {session.label}\nDuur: {session.duration_s:.1f}s\nEvents: {session.point_count:,}\nIn profiel: {'ja' if session.included else 'nee'}\nPad-overeenkomst demo: {score:.1f}%")

    def _bounds_from_points(self, points):
        if not points:
            return virtual_screen_bounds()
        xs = [p[1] for p in points]
        ys = [p[2] for p in points]
        left, right = min(xs), max(xs)
        top, bottom = min(ys), max(ys)
        return (int(left), int(top), max(1, int(right - left)), max(1, int(bottom - top)))

    def toggle_replay(self):
        if self.replay_running:
            self.pause_replay()
        else:
            self.start_replay()

    def start_replay(self):
        if len(self.replay_points) < 2:
            messagebox.showinfo("Replay", "Selecteer eerst een geldige opname.")
            return
        self.replay_running = True
        self.play_btn.config(text="Ⅱ Pauze")
        self._replay_step()

    def pause_replay(self):
        self.replay_running = False
        if hasattr(self, "play_btn"):
            self.play_btn.config(text="▶ Replay")
        if self.replay_after:
            try:
                self.root.after_cancel(self.replay_after)
            except tk.TclError:
                pass
            self.replay_after = None

    def restart_replay(self):
        self._clear_trace()
        if self.replay_points:
            self.start_replay()

    def _replay_step(self):
        if not self.replay_running or self.replay_index >= len(self.replay_points):
            self.pause_replay()
            return
        current = self.replay_points[self.replay_index]
        event = MouseEvent(current[0], "move", current[1], current[2])
        self._draw_live_point(event)
        self.replay_index += 1
        self._draw_progress()
        if self.replay_index < len(self.replay_points):
            prev_t = current[0]
            next_t = self.replay_points[self.replay_index][0]
            delay = max(1, min(80, int((next_t - prev_t) * 1000 / max(0.1, self.speed_var.get()))))
        else:
            delay = 1
        self.replay_after = self.root.after(delay, self._replay_step)

    def _draw_progress(self):
        self.progress.delete("all")
        w = max(100, self.progress.winfo_width())
        self.progress.create_line(8, 12, w - 8, 12, fill="#283750", width=4)
        ratio = 0.0 if not self.replay_points else self.replay_index / len(self.replay_points)
        self.progress.create_line(8, 12, 8 + (w - 16) * ratio, 12, fill=PURPLE, width=4)
        x = 8 + (w - 16) * ratio
        self.progress.create_oval(x - 6, 6, x + 6, 18, fill="#d9d0ff", outline=PURPLE)

    def build_profile_async(self):
        self.system_status.config(text="● Profiel wordt gebouwd", fg=CYAN)
        def worker():
            try:
                profile = build_master_profile(list_sessions())
                self.root.after(0, lambda p=profile: self._profile_done(p))
            except Exception as exc:
                text = str(exc)
                self.root.after(0, lambda t=text: messagebox.showerror("Profiel", t))
        threading.Thread(target=worker, daemon=True).start()

    def _profile_done(self, profile):
        self.system_status.config(text="● Profiel gereed", fg=GREEN)
        self.refresh()
        messagebox.showinfo("Profiel", f"Gebouwd uit {profile['source_count']} sessies.")

    def run_stress_async(self):
        self.system_status.config(text="● 100 simulaties draaien", fg=CYAN)
        def worker():
            try:
                report = run_stress_test(100, 42)
                self.root.after(0, lambda r=report: self._stress_done(r))
            except Exception as exc:
                text = str(exc)
                self.root.after(0, lambda t=text: messagebox.showerror("Stress Lab", t))
        threading.Thread(target=worker, daemon=True).start()

    def _stress_done(self, report):
        self.system_status.config(text="● Stress Lab gereed", fg=GREEN)
        scores = report["scores"]
        messagebox.showinfo("Profile Stress Lab", f"Overall: {scores['overall']}/100\nProfielmatch: {scores['profile_similarity']}\nHerhalingscontrole: {scores['repetition_control']}\n\n{report['result_folder']}")

    def on_close(self):
        if self.recorder.running:
            if not messagebox.askyesno("AI Mouse", "Er loopt nog een opname. Stoppen zonder opslaan?"):
                return
            self.recorder.stop()
        self.pause_replay()
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
