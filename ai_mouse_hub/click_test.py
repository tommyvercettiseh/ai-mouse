from __future__ import annotations

import math
import random
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox
from typing import Sequence

from .core import generate_replay, load_master_profile

BG = "#07101d"
PANEL = "#0d1928"
TEXT = "#f5f7ff"
MUTED = "#8d9bb0"
BORDER = "#20324a"
BLUE = "#3478ff"
PURPLE = "#8b4dff"
CYAN = "#18c7e8"
GREEN = "#42d67b"
RED = "#ef4a56"


@dataclass(frozen=True)
class ClickResult:
    target_index: int
    direct_distance: float
    travelled_distance: float
    overshoot_px: float
    corrections: int
    hit_distance_px: float


def transform_template(
    template: Sequence[Sequence[float]],
    start: tuple[float, float],
    target: tuple[float, float],
    rng: random.Random,
) -> list[tuple[float, float]]:
    """Map a normalized profile template from start to target inside the local canvas."""
    if len(template) < 2:
        return [start, target]
    normalized = [(float(p[0]), float(p[1])) for p in template]
    generated = generate_replay(normalized, rng, strength=rng.uniform(0.012, 0.032))
    sx, sy = generated[0]
    ex, ey = generated[-1]
    base_dx, base_dy = ex - sx, ey - sy
    base_len = math.hypot(base_dx, base_dy)
    tx, ty = target[0] - start[0], target[1] - start[1]
    target_len = max(1.0, math.hypot(tx, ty))
    if base_len < 1e-6:
        return [start, target]
    base_angle = math.atan2(base_dy, base_dx)
    target_angle = math.atan2(ty, tx)
    angle = target_angle - base_angle
    scale = target_len / base_len
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    out: list[tuple[float, float]] = []
    for x, y in generated:
        px, py = (x - sx) * scale, (y - sy) * scale
        rx = px * cos_a - py * sin_a
        ry = px * sin_a + py * cos_a
        out.append((start[0] + rx, start[1] + ry))
    out[0] = start
    out[-1] = target
    return out


def path_metrics(path: Sequence[tuple[float, float]], target: tuple[float, float], target_radius: float) -> ClickResult:
    if len(path) < 2:
        return ClickResult(0, 0.0, 0.0, 0.0, 0, 0.0)
    direct = math.hypot(path[-1][0] - path[0][0], path[-1][1] - path[0][1])
    travelled = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:]))
    distances = [math.hypot(x - target[0], y - target[1]) for x, y in path]
    first_entry = next((i for i, distance in enumerate(distances) if distance <= target_radius), len(path) - 1)
    overshoot = max((distance for distance in distances[first_entry:] if distance > target_radius), default=target_radius) - target_radius
    corrections = 0
    previous = None
    for distance in distances[first_entry:]:
        trend = 1 if previous is not None and distance > previous else -1
        if previous is not None and trend > 0:
            corrections += 1
        previous = distance
    return ClickResult(0, direct, travelled, max(0.0, overshoot), corrections, distances[-1])


class ClickTestApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AI Mouse – Profile Click Test")
        self.root.geometry("1280x780")
        self.root.minsize(980, 650)
        self.root.configure(bg=BG)

        self.profile = load_master_profile()
        self.templates = self.profile.get("templates") or []
        self.rng = random.Random(42)
        self.running = False
        self.after_id: str | None = None
        self.targets: list[tuple[float, float]] = []
        self.current_target = 0
        self.current_path: list[tuple[float, float]] = []
        self.path_index = 0
        self.cursor = (120.0, 120.0)
        self.results: list[ClickResult] = []
        self.trace_items: list[int] = []
        self.trace_history: list[tuple[float, float]] = []

        self._build()
        self._refresh_profile_status()

    def _button(self, parent, text, command, bg=PANEL, **kwargs):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=TEXT, activebackground=bg,
                         activeforeground=TEXT, relief="flat", cursor="hand2", font=("Segoe UI", 10, "bold"), **kwargs)

    def _build(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=20, pady=(18, 10))
        tk.Label(header, text="Profile Click Test", bg=BG, fg=TEXT, font=("Segoe UI", 21, "bold")).pack(side="left")
        self.profile_label = tk.Label(header, text="", bg=BG, fg=MUTED, font=("Segoe UI", 9))
        self.profile_label.pack(side="right")

        controls = tk.Frame(self.root, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        controls.pack(fill="x", padx=20, pady=(0, 10))
        inner = tk.Frame(controls, bg=PANEL)
        inner.pack(fill="x", padx=14, pady=12)
        self.start_btn = self._button(inner, "▶ Start test", self.start_test, bg=PURPLE, padx=20, pady=9)
        self.start_btn.pack(side="left")
        self.stop_btn = self._button(inner, "■ Stop", self.stop_test, padx=18, pady=9, state="disabled")
        self.stop_btn.pack(side="left", padx=8)
        tk.Label(inner, text="Targets", bg=PANEL, fg=MUTED).pack(side="left", padx=(20, 6))
        self.target_var = tk.IntVar(value=20)
        tk.Spinbox(inner, from_=5, to=100, textvariable=self.target_var, width=5, bg="#132238", fg=TEXT,
                   buttonbackground="#132238", relief="flat").pack(side="left")
        tk.Label(inner, text="Snelheid", bg=PANEL, fg=MUTED).pack(side="left", padx=(20, 6))
        self.speed_var = tk.DoubleVar(value=1.0)
        tk.Scale(inner, from_=0.25, to=4.0, resolution=0.25, orient="horizontal", variable=self.speed_var,
                 bg=PANEL, fg=TEXT, troughcolor="#25334a", highlightthickness=0, length=150).pack(side="left")
        self.status = tk.Label(inner, text="Klaar", bg=PANEL, fg=GREEN, font=("Segoe UI", 9, "bold"))
        self.status.pack(side="right")

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        body.grid_columnconfigure(0, weight=4)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        stage = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        stage.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.canvas = tk.Canvas(stage, bg="#050c16", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=12)
        self.canvas.bind("<Configure>", lambda _e: self._draw_background())

        side = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, width=260)
        side.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        side.grid_propagate(False)
        tk.Label(side, text="Laatste actie", bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(16, 10))
        self.metrics = tk.Label(side, text="Start de test om het pad te zien.", bg=PANEL, fg=MUTED,
                                justify="left", anchor="nw", font=("Segoe UI", 10), wraplength=220)
        self.metrics.pack(fill="x", padx=16)
        tk.Frame(side, bg=BORDER, height=1).pack(fill="x", padx=16, pady=16)
        tk.Label(side, text="Legenda", bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16)
        legend = "Blauw   approach\nPaars   correctie / overshoot\nGroen   klikmoment\nGrijs    directe lijn"
        tk.Label(side, text=legend, bg=PANEL, fg=MUTED, justify="left", font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=10)
        self.summary = tk.Label(side, text="", bg=PANEL, fg=TEXT, justify="left", font=("Segoe UI", 9))
        self.summary.pack(anchor="w", padx=16, pady=(20, 0))

    def _refresh_profile_status(self):
        if self.templates:
            self.profile_label.config(text=f"Profiel geladen · {self.profile.get('source_count', 0)} bron(n)", fg=GREEN)
        else:
            self.profile_label.config(text="Geen masterprofiel", fg=RED)

    def _draw_background(self):
        self.canvas.delete("grid")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        for x in range(0, w, 50):
            self.canvas.create_line(x, 0, x, h, fill="#0b1725", tags="grid")
        for y in range(0, h, 50):
            self.canvas.create_line(0, y, w, y, fill="#0b1725", tags="grid")
        self.canvas.tag_lower("grid")

    def _make_targets(self, count: int):
        self.targets.clear()
        w, h = max(500, self.canvas.winfo_width()), max(400, self.canvas.winfo_height())
        margin = 70
        for _ in range(count):
            self.targets.append((self.rng.uniform(margin, w - margin), self.rng.uniform(margin, h - margin)))

    def _draw_targets(self):
        self.canvas.delete("target")
        radius = 20
        for index, (x, y) in enumerate(self.targets):
            active = index == self.current_target
            outline = PURPLE if active else "#3a475a"
            width = 3 if active else 1
            self.canvas.create_rectangle(x-radius, y-radius, x+radius, y+radius, outline=outline, width=width, tags="target")
            self.canvas.create_text(x, y, text=str(index + 1), fill=TEXT if active else MUTED, font=("Segoe UI", 9, "bold"), tags="target")

    def start_test(self):
        if not self.templates:
            messagebox.showwarning("Profile Click Test", "Bouw eerst een masterprofiel in AI Mouse Hub.")
            return
        self.stop_test()
        self.canvas.delete("path")
        self.canvas.delete("click")
        self.trace_items.clear()
        self.trace_history.clear()
        self.results.clear()
        self.current_target = 0
        self.cursor = (120.0, 120.0)
        self._make_targets(max(5, min(100, int(self.target_var.get()))))
        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status.config(text="Test actief", fg=GREEN)
        self._draw_targets()
        self._prepare_action()

    def stop_test(self):
        self.running = False
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if hasattr(self, "start_btn"):
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
        if hasattr(self, "status"):
            self.status.config(text="Gestopt", fg=MUTED)

    def _prepare_action(self):
        if not self.running:
            return
        if self.current_target >= len(self.targets):
            self.running = False
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.status.config(text="Voltooid", fg=GREEN)
            self._update_summary()
            return
        target = self.targets[self.current_target]
        template = self.templates[self.rng.randrange(len(self.templates))]
        self.current_path = transform_template(template, self.cursor, target, self.rng)
        self.path_index = 0
        self._draw_targets()
        self.canvas.create_line(self.cursor[0], self.cursor[1], target[0], target[1], fill="#536174", dash=(4, 5), tags="path")
        self._animate_step()

    def _animate_step(self):
        if not self.running or self.path_index >= len(self.current_path):
            if self.running:
                self._finish_action()
            return
        point = self.current_path[self.path_index]
        previous = self.cursor if self.path_index == 0 else self.current_path[self.path_index - 1]
        target = self.targets[self.current_target]
        distance = math.hypot(point[0] - target[0], point[1] - target[1])
        color = BLUE if distance > 28 else PURPLE
        line = self.canvas.create_line(previous[0], previous[1], point[0], point[1], fill=color, width=3, smooth=True, tags="path")
        self.trace_items.append(line)
        self.trace_history.append(point)
        self.canvas.delete("cursor")
        self.canvas.create_oval(point[0]-7, point[1]-7, point[0]+7, point[1]+7, fill=CYAN, outline="white", width=1, tags="cursor")
        self._fade_trace()
        self.path_index += 1
        delay = max(4, int(18 / max(0.25, float(self.speed_var.get()))))
        self.after_id = self.root.after(delay, self._animate_step)

    def _fade_trace(self):
        palette = ["#132238", "#1e3463", "#2f4fa3", BLUE, PURPLE]
        for offset, item in enumerate(self.trace_items[-80:]):
            age = len(self.trace_items[-80:]) - offset - 1
            self.canvas.itemconfigure(item, fill=palette[max(0, min(len(palette)-1, 4 - age // 16))])
        while len(self.trace_items) > 80:
            old = self.trace_items.pop(0)
            self.canvas.delete(old)

    def _finish_action(self):
        target = self.targets[self.current_target]
        metrics = path_metrics(self.current_path, target, 20.0)
        result = ClickResult(self.current_target + 1, metrics.direct_distance, metrics.travelled_distance,
                             metrics.overshoot_px, metrics.corrections, metrics.hit_distance_px)
        self.results.append(result)
        self.cursor = target
        self.canvas.create_oval(target[0]-10, target[1]-10, target[0]+10, target[1]+10, fill=GREEN, outline="", tags="click")
        self.metrics.config(text=(
            f"Target: {result.target_index}\n\n"
            f"Directe afstand: {result.direct_distance:.1f} px\n"
            f"Werkelijk pad: {result.travelled_distance:.1f} px\n"
            f"Overshoot: {result.overshoot_px:.1f} px\n"
            f"Correcties: {result.corrections}\n"
            f"Klikafstand: {result.hit_distance_px:.1f} px"
        ))
        self.current_target += 1
        self._update_summary()
        self.after_id = self.root.after(350, self._prepare_action)

    def _update_summary(self):
        if not self.results:
            self.summary.config(text="")
            return
        avg_over = sum(r.overshoot_px for r in self.results) / len(self.results)
        avg_path = sum(r.travelled_distance / max(1.0, r.direct_distance) for r in self.results) / len(self.results)
        self.summary.config(text=(
            f"Voortgang: {len(self.results)}/{len(self.targets)}\n"
            f"Gem. overshoot: {avg_over:.1f} px\n"
            f"Gem. padfactor: {avg_path:.2f}×"
        ))


def main():
    root = tk.Tk()
    ClickTestApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
