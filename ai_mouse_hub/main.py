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
    save_recording,
    set_included,
    similarity,
)

BG = "#08111f"
PANEL = "#101b2d"
PANEL2 = "#142238"
TEXT = "#f5f7ff"
MUTED = "#91a0b8"
BLUE = "#3677ff"
PURPLE = "#8b4dff"
RED = "#ff4d5f"
GREEN = "#40d98b"
BORDER = "#24344f"


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.points: list[tuple[float, float, float]] = []
        self.recording = False
        self.started_at = 0.0
        self.sessions = []
        self.session_by_item = {}
        self.root.title("AI Mouse Profile Hub")
        self.root.geometry("1400x880")
        self.root.minsize(1100, 720)
        self.root.configure(bg=BG)
        self._styles()
        self._build()
        self.refresh()

    def _styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=PANEL, foreground=TEXT, fieldbackground=PANEL, rowheight=32)
        style.configure("Treeview.Heading", background=PANEL2, foreground=MUTED)
        style.map("Treeview", background=[("selected", "#23427a")])

    def button(self, parent, text, command, bg=PANEL2, **kwargs):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=TEXT, activebackground=bg,
                         activeforeground=TEXT, relief="flat", cursor="hand2", **kwargs)

    def panel(self, parent, title):
        frame = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        tk.Label(frame, text=title, bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(12, 8))
        return frame

    def _build(self):
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True, padx=16, pady=16)
        tk.Label(shell, text="AI Mouse Profile Hub", bg=BG, fg=TEXT, font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(shell, text="Standalone recorder, replay en quality stress testing", bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 14))

        grid = tk.Frame(shell, bg=BG)
        grid.pack(fill="both", expand=True)
        grid.grid_columnconfigure(0, weight=4)
        grid.grid_columnconfigure(1, weight=6)
        grid.grid_rowconfigure(0, weight=1)
        grid.grid_rowconfigure(1, weight=1)

        record = self.panel(grid, "1  Record inside local canvas")
        record.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        controls = tk.Frame(record, bg=PANEL)
        controls.pack(fill="x", padx=14)
        self.label_var = tk.StringVar(value="Browsing")
        ttk.Combobox(controls, textvariable=self.label_var, values=("Browsing", "Precision", "Fast", "Relaxed", "Fatigued"), state="normal").pack(side="left", fill="x", expand=True)
        self.start_btn = self.button(controls, "Start", self.start_recording, bg=RED, padx=16, pady=7)
        self.start_btn.pack(side="left", padx=(8, 0))
        self.stop_btn = self.button(controls, "Stop & Save", self.stop_recording, bg=BLUE, padx=16, pady=7, state="disabled")
        self.stop_btn.pack(side="left", padx=(8, 0))
        self.canvas = tk.Canvas(record, bg="#07101d", highlightbackground=BORDER, highlightthickness=1)
        self.canvas.pack(fill="both", expand=True, padx=14, pady=14)
        self.canvas.bind("<Motion>", self.on_motion)

        sessions = self.panel(grid, "2  Sessions")
        sessions.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 8))
        columns = ("created", "label", "duration", "points", "included")
        self.tree = ttk.Treeview(sessions, columns=columns, show="headings", selectmode="browse")
        for col, title, width in (("created", "Created", 180), ("label", "Label", 120), ("duration", "Duration", 90), ("points", "Points", 80), ("included", "Profile", 80)):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width)
        self.tree.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.draw_replay())
        actions = tk.Frame(sessions, bg=PANEL)
        actions.pack(fill="x", padx=14, pady=(0, 12))
        self.button(actions, "Toggle included", self.toggle_selected, padx=12, pady=6).pack(side="left")
        self.button(actions, "Refresh", self.refresh, padx=12, pady=6).pack(side="right")

        profile = self.panel(grid, "3  Master profile")
        profile.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(8, 0))
        self.profile_text = tk.Label(profile, text="No profile", bg=PANEL, fg=MUTED, justify="left", font=("Segoe UI", 10))
        self.profile_text.pack(anchor="w", padx=14, pady=(0, 12))
        self.build_btn = self.button(profile, "Build profile from included sessions", self.build_profile_async, bg=BLUE, pady=9)
        self.build_btn.pack(fill="x", padx=14, pady=(0, 10))
        self.stress_btn = self.button(profile, "Run 100x Profile Stress Lab", self.run_stress_async, bg=PURPLE, pady=9)
        self.stress_btn.pack(fill="x", padx=14, pady=(0, 14))
        self.status = tk.Label(profile, text="Ready", bg=PANEL, fg=GREEN)
        self.status.pack(anchor="w", padx=14, pady=(0, 12))

        replay = self.panel(grid, "4  Replay compare")
        replay.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=(8, 0))
        canvases = tk.Frame(replay, bg=PANEL)
        canvases.pack(fill="both", expand=True, padx=14)
        canvases.grid_columnconfigure(0, weight=1)
        canvases.grid_columnconfigure(1, weight=1)
        canvases.grid_rowconfigure(0, weight=1)
        self.real_canvas = tk.Canvas(canvases, bg="#07101d", highlightbackground=BORDER, highlightthickness=1)
        self.real_canvas.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.profile_canvas = tk.Canvas(canvases, bg="#07101d", highlightbackground=BORDER, highlightthickness=1)
        self.profile_canvas.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.score_label = tk.Label(replay, text="Select a session", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold"))
        self.score_label.pack(anchor="w", padx=14, pady=12)

    def start_recording(self):
        self.points.clear()
        self.started_at = time.perf_counter()
        self.recording = True
        self.canvas.delete("all")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status.config(text="Recording… move inside the canvas", fg=RED)

    def on_motion(self, event):
        if not self.recording:
            return
        now = time.perf_counter() - self.started_at
        self.points.append((now, float(event.x), float(event.y)))
        if len(self.points) > 1:
            _, x1, y1 = self.points[-2]
            self.canvas.create_line(x1, y1, event.x, event.y, fill="#dfe8ff", width=2)

    def stop_recording(self):
        self.recording = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        if len(self.points) < 10:
            messagebox.showwarning("Recording", "Move a little longer before saving.")
            return
        folder = save_recording(self.label_var.get(), self.points)
        self.status.config(text=f"Saved: {folder.name}", fg=GREEN)
        self.refresh()

    def refresh(self):
        self.sessions = list_sessions()
        self.session_by_item.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for session in self.sessions:
            item = self.tree.insert("", "end", values=(session.created, session.label, f"{session.duration_s:.1f}s", session.point_count, "Yes" if session.included else "No"))
            self.session_by_item[item] = session
        profile = load_master_profile()
        if profile:
            self.profile_text.config(text=f"Version: {profile.get('profile_version')}\nSources: {profile.get('source_count')}\nLabels: {', '.join(profile.get('labels') or [])}")
        else:
            self.profile_text.config(text="No master profile yet")

    def selected(self):
        selection = self.tree.selection()
        return self.session_by_item.get(selection[0]) if selection else None

    def toggle_selected(self):
        session = self.selected()
        if session is None:
            return
        set_included(session, not session.included)
        self.refresh()

    def draw_path(self, canvas, path, title):
        canvas.delete("all")
        w, h = max(300, canvas.winfo_width()), max(180, canvas.winfo_height())
        canvas.create_text(12, 12, text=title, fill=MUTED, anchor="nw")
        if not path:
            return
        points = [(25 + x*(w-50), 25 + y*(h-50)) for x, y in path]
        flat = [v for point in points for v in point]
        canvas.create_line(*flat, fill="#eaf0ff", width=2, smooth=True)
        sx, sy = points[0]
        ex, ey = points[-1]
        canvas.create_oval(sx-5, sy-5, sx+5, sy+5, fill=PURPLE, outline="")
        canvas.create_oval(ex-10, ey-10, ex+10, ey+10, outline=RED, width=3)

    def draw_replay(self):
        session = self.selected()
        if session is None:
            return
        real = normalize_path(load_points(session.folder / "points.csv"))
        profile = load_master_profile()
        rng = random.Random(42)
        generated = generate_replay(real, rng)
        self.draw_path(self.real_canvas, real, "Real recording")
        self.draw_path(self.profile_canvas, generated, "Profile replay")
        self.score_label.config(text=f"Path similarity: {similarity(real, generated):.1f}%")

    def build_profile_async(self):
        self.build_btn.config(state="disabled")
        self.status.config(text="Building profile…", fg=TEXT)
        def worker():
            try:
                profile = build_master_profile(list_sessions())
                self.root.after(0, lambda: self._done(f"Built from {profile['source_count']} sessions"))
            except Exception as exc:
                self.root.after(0, lambda: self._error(str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def run_stress_async(self):
        self.stress_btn.config(state="disabled")
        self.status.config(text="Running 100 simulated profiles…", fg=TEXT)
        def worker():
            try:
                report = run_stress_test(100, 42)
                self.root.after(0, lambda: self._stress_done(report))
            except Exception as exc:
                self.root.after(0, lambda: self._error(str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def _done(self, text):
        self.build_btn.config(state="normal")
        self.status.config(text=text, fg=GREEN)
        self.refresh()

    def _stress_done(self, report):
        self.stress_btn.config(state="normal")
        self.status.config(text=f"Stress score: {report['scores']['overall']}/100", fg=GREEN)
        messagebox.showinfo("Profile Stress Lab", f"Overall: {report['scores']['overall']}/100\nSimilarity: {report['scores']['profile_similarity']}\nRepetition control: {report['scores']['repetition_control']}\n\n{report['result_folder']}")

    def _error(self, text):
        self.build_btn.config(state="normal")
        self.stress_btn.config(state="normal")
        self.status.config(text="Failed", fg=RED)
        messagebox.showerror("AI Mouse Hub", text)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
