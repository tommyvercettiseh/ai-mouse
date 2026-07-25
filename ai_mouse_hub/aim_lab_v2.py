from __future__ import annotations

import json
import math
import random
import statistics
import time
import tkinter as tk
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from tkinter import ttk

from .core import DATA

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
REPORTS = DATA / "aim_lab"
REPORTS.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class ActionMetrics:
    direct_distance: float
    travelled_distance: float
    overshoot_px: float
    corrections: int
    final_offset_px: float
    reaction_ms: float
    movement_ms: float
    click_delay_ms: float
    click_hold_ms: float
    mean_speed_px_s: float
    peak_speed_px_s: float
    accuracy_percent: float


def _triangle_points(target: tuple[float, float], radius: float) -> tuple[tuple[float, float], ...]:
    x, y = target
    return ((x, y - radius), (x - radius, y + radius), (x + radius, y + radius))


def _inside_triangle(x: float, y: float, target: tuple[float, float], radius: float) -> bool:
    a, b, c = _triangle_points(target, radius)

    def sign(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

    point = (x, y)
    d1, d2, d3 = sign(point, a, b), sign(point, b, c), sign(point, c, a)
    has_negative = d1 < 0 or d2 < 0 or d3 < 0
    has_positive = d1 > 0 or d2 > 0 or d3 > 0
    return not (has_negative and has_positive)


def _inside_target(x: float, y: float, target: tuple[float, float], radius: float, shape: str) -> bool:
    dx, dy = x - target[0], y - target[1]
    if shape == "circle":
        return dx * dx + dy * dy <= radius * radius
    if shape == "triangle":
        return _inside_triangle(x, y, target, radius)
    return abs(dx) <= radius and abs(dy) <= radius


def path_metrics(
    path: list[tuple[float, float, float]],
    target: tuple[float, float],
    radius: float,
    click_delay: float,
    reaction_s: float = 0.0,
    click_hold_s: float = 0.0,
) -> ActionMetrics:
    if len(path) < 2:
        return ActionMetrics(0, 0, 0, 0, 0, reaction_s * 1000, 0, click_delay * 1000,
                             click_hold_s * 1000, 0, 0, 0)

    xy = [(x, y) for _, x, y in path]
    direct = max(1.0, math.dist(xy[0], target))
    travelled = sum(math.dist(a, b) for a, b in zip(xy, xy[1:]))
    distances = [math.dist(point, target) for point in xy]
    first_entry = next((i for i, value in enumerate(distances) if value <= radius), len(distances) - 1)
    tail = distances[first_entry:]
    overshoot = max(0.0, max(tail, default=radius) - radius)

    corrections = 0
    for a, b, c in zip(tail, tail[1:], tail[2:]):
        if b < a and c > b + max(0.8, radius * 0.03):
            corrections += 1

    speeds: list[float] = []
    for a, b in zip(path, path[1:]):
        dt = max(0.001, b[0] - a[0])
        speeds.append(math.dist((a[1], a[2]), (b[1], b[2])) / dt)

    duration = max(0.0, path[-1][0] - path[0][0])
    final_offset = distances[-1]
    accuracy = max(0.0, min(100.0, 100.0 * (1.0 - final_offset / max(1.0, radius))))
    return ActionMetrics(
        direct_distance=direct,
        travelled_distance=travelled,
        overshoot_px=overshoot,
        corrections=corrections,
        final_offset_px=final_offset,
        reaction_ms=reaction_s * 1000,
        movement_ms=duration * 1000,
        click_delay_ms=click_delay * 1000,
        click_hold_ms=click_hold_s * 1000,
        mean_speed_px_s=statistics.fmean(speeds) if speeds else 0.0,
        peak_speed_px_s=max(speeds, default=0.0),
        accuracy_percent=accuracy,
    )


class AimLabApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AI Mouse – Aim Lab")
        self.root.geometry("1040x700")
        self.root.minsize(860, 600)
        self.root.configure(bg=BG)

        self.rng = random.Random()
        self.running = False
        self.target_total = 20
        self.target_index = 0
        self.target = (500.0, 320.0)
        self.target_radius = 26.0
        self.target_shape = "circle"
        self.previous_target: tuple[float, float] | None = None
        self.cursor = (110.0, 110.0)
        self.path: list[tuple[float, float, float]] = []
        self.target_spawned_at = 0.0
        self.first_move_at: float | None = None
        self.last_move_at: float | None = None
        self.mouse_down_at: float | None = None
        self.current_misses = 0
        self.current_resets = 0
        self.results: list[dict] = []
        self.session_folder: Path | None = None

        self.count_var = tk.IntVar(value=20)
        self._build()
        self._redraw()

    def _button(self, parent, text, command, bg=PANEL_2, **kwargs):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=TEXT,
                         activebackground=bg, activeforeground=TEXT, relief="flat", bd=0,
                         cursor="hand2", font=("Segoe UI", 10, "bold"), **kwargs)

    def _build(self) -> None:
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True, padx=18, pady=16)

        header = tk.Frame(shell, bg=BG)
        header.pack(fill="x", pady=(0, 12))
        tk.Label(header, text="Aim Lab", bg=BG, fg=TEXT, font=("Segoe UI", 23, "bold")).pack(side="left")
        tk.Label(header, text="Klik zelf · targets wisselen automatisch", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="right")

        controls = tk.Frame(shell, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        controls.pack(fill="x", pady=(0, 10))
        row = tk.Frame(controls, bg=PANEL)
        row.pack(fill="x", padx=14, pady=11)
        self.start_btn = self._button(row, "▶  Start test", self.start, bg=PURPLE, padx=20, pady=9)
        self.start_btn.pack(side="left")
        self.stop_btn = self._button(row, "■  Stop", self.stop, padx=16, pady=9, state="disabled")
        self.stop_btn.pack(side="left", padx=8)
        tk.Label(row, text="Targets", bg=PANEL, fg=MUTED).pack(side="left", padx=(14, 5))
        tk.Spinbox(row, from_=5, to=200, textvariable=self.count_var, width=6, bg=PANEL_2, fg=TEXT,
                   buttonbackground=PANEL_2, relief="flat").pack(side="left")
        self.status = tk.Label(row, text="Klaar", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold"))
        self.status.pack(side="right")

        body = tk.Frame(shell, bg=BG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=4)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        stage = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        stage.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.canvas = tk.Canvas(stage, bg="#050c16", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True, padx=12, pady=12)
        self.canvas.bind("<Configure>", lambda _e: self._redraw())
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._reset_current_action)

        side = tk.Frame(body, bg=PANEL, width=250, highlightbackground=BORDER, highlightthickness=1)
        side.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        side.grid_propagate(False)
        tk.Label(side, text="Resultaten", bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(16, 8))
        self.metrics_label = tk.Label(side, text="Start de test.", bg=PANEL, fg=MUTED,
                                      justify="left", anchor="nw", wraplength=215, font=("Segoe UI", 9))
        self.metrics_label.pack(fill="x", padx=16)
        tk.Frame(side, bg=BORDER, height=1).pack(fill="x", padx=16, pady=16)
        tk.Label(side, text="Automatische variatie:\n• rond, vierkant, driehoek\n• klein, middel, groot\n• korte en lange afstanden\n• randen, hoeken en diagonalen\n\nRechtermuisknop reset alleen het huidige target.",
                 bg=PANEL, fg=MUTED, justify="left", wraplength=215, font=("Segoe UI", 9)).pack(anchor="w", padx=16)
        self.summary_label = tk.Label(side, text="", bg=PANEL, fg=TEXT, justify="left", font=("Segoe UI", 9))
        self.summary_label.pack(anchor="w", padx=16, pady=(20, 0))

    def _new_target(self) -> None:
        w, h = max(500, self.canvas.winfo_width()), max(400, self.canvas.winfo_height())
        size_group = self.rng.choices(("small", "medium", "large"), weights=(4, 4, 2), k=1)[0]
        ranges = {"small": (10, 17), "medium": (22, 34), "large": (42, 62)}
        self.target_radius = self.rng.uniform(*ranges[size_group])
        self.target_shape = self.rng.choice(("circle", "square", "triangle"))
        margin = self.target_radius + 30

        candidates = [
            (margin, margin), (w - margin, margin),
            (margin, h - margin), (w - margin, h - margin),
            (w * 0.5, margin), (w * 0.5, h - margin),
            (margin, h * 0.5), (w - margin, h * 0.5),
            (w * 0.5, h * 0.5),
        ]
        origin = self.previous_target or self.cursor
        distance_mode = self.rng.choices(("short", "medium", "long"), weights=(3, 3, 4), k=1)[0]
        diagonal = math.hypot(w, h)
        if distance_mode == "short":
            pool = [p for p in candidates if math.dist(origin, p) < diagonal * 0.30]
        elif distance_mode == "long":
            pool = [p for p in candidates if math.dist(origin, p) > diagonal * 0.52]
        else:
            pool = [p for p in candidates if diagonal * 0.25 <= math.dist(origin, p) <= diagonal * 0.58]
        base = self.rng.choice(pool or candidates)
        jitter = min(45.0, max(7.0, self.target_radius * 0.65))
        self.target = (
            min(w - margin, max(margin, base[0] + self.rng.uniform(-jitter, jitter))),
            min(h - margin, max(margin, base[1] + self.rng.uniform(-jitter, jitter))),
        )
        self.previous_target = self.target

    def start(self) -> None:
        self.stop()
        self.target_total = max(5, min(200, int(self.count_var.get())))
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.session_folder = REPORTS / f"{stamp}_human"
        self.session_folder.mkdir(parents=True, exist_ok=False)
        self.results.clear()
        self.target_index = 0
        self.previous_target = None
        self.cursor = (110.0, 110.0)
        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status.config(text="Test actief", fg=GREEN)
        self._prepare_target()

    def stop(self) -> None:
        self.running = False
        if hasattr(self, "start_btn"):
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")

    def _prepare_target(self) -> None:
        if not self.running:
            return
        if self.target_index >= self.target_total:
            self._complete()
            return
        self._new_target()
        self.path = []
        self.first_move_at = None
        self.last_move_at = None
        self.mouse_down_at = None
        self.current_misses = 0
        self.current_resets = 0
        self.target_spawned_at = time.perf_counter()
        self.status.config(text=f"Target {self.target_index + 1}/{self.target_total}", fg=GREEN)
        self._redraw()

    def _on_motion(self, event) -> None:
        if not self.running:
            return
        now = time.perf_counter()
        if self.first_move_at is None:
            self.first_move_at = now
        self.last_move_at = now
        self.cursor = (float(event.x), float(event.y))
        self.path.append((now - self.target_spawned_at, float(event.x), float(event.y)))
        self._redraw()

    def _on_press(self, _event) -> None:
        if self.running:
            self.mouse_down_at = time.perf_counter()

    def _on_release(self, event) -> None:
        if not self.running or self.mouse_down_at is None:
            return
        released_at = time.perf_counter()
        mouse_down = self.mouse_down_at
        self.mouse_down_at = None

        if not _inside_target(event.x, event.y, self.target, self.target_radius, self.target_shape):
            self.current_misses += 1
            self.status.config(text=f"Mis ({self.current_misses}) · probeer opnieuw", fg=RED)
            return

        if len(self.path) < 2:
            self.path = [(0.0, float(event.x), float(event.y)), (0.001, float(event.x), float(event.y))]
        click_delay = max(0.0, mouse_down - (self.last_move_at or mouse_down))
        reaction = max(0.0, (self.first_move_at or mouse_down) - self.target_spawned_at)
        hold = max(0.0, released_at - mouse_down)
        metrics = path_metrics(self.path, self.target, self.target_radius, click_delay, reaction, hold)
        self._save_action(metrics)
        self.cursor = (float(event.x), float(event.y))
        self.target_index += 1
        self.root.after(180, self._prepare_target)

    def _reset_current_action(self, _event=None) -> None:
        if not self.running:
            return
        self.current_resets += 1
        self.path = []
        self.first_move_at = None
        self.last_move_at = None
        self.mouse_down_at = None
        self.target_spawned_at = time.perf_counter()
        self.status.config(text="Huidige target gereset", fg=PURPLE)
        self._redraw()

    def _save_action(self, metrics: ActionMetrics) -> None:
        record = {
            "target_index": self.target_index + 1,
            "target": {"x": self.target[0], "y": self.target[1], "radius": self.target_radius, "shape": self.target_shape},
            "metrics": asdict(metrics),
            "misses": self.current_misses,
            "resets": self.current_resets,
            "path": [[round(t, 6), round(x, 3), round(y, 3)] for t, x, y in self.path],
        }
        self.results.append(record)
        if self.session_folder:
            with (self.session_folder / "actions.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")

        self.metrics_label.config(text=(
            f"Target {self.target_index + 1}/{self.target_total}\n\n"
            f"Vorm: {self.target_shape}\n"
            f"Grootte: {self.target_radius:.0f} px\n"
            f"Accuracy: {metrics.accuracy_percent:.0f}%\n"
            f"Overshoot: {metrics.overshoot_px:.1f} px\n"
            f"Correcties: {metrics.corrections}\n"
            f"Reactie: {metrics.reaction_ms:.0f} ms\n"
            f"Beweging: {metrics.movement_ms:.0f} ms\n"
            f"Klikdelay: {metrics.click_delay_ms:.0f} ms\n"
            f"Klikhold: {metrics.click_hold_ms:.0f} ms\n"
            f"Gem. snelheid: {metrics.mean_speed_px_s:.0f} px/s\n"
            f"Piek: {metrics.peak_speed_px_s:.0f} px/s\n"
            f"Misklikken: {self.current_misses}"
        ))
        self._update_summary()

    def _update_summary(self) -> None:
        if not self.results:
            return
        metrics = [item["metrics"] for item in self.results]
        average = lambda key: statistics.fmean(float(item[key]) for item in metrics)
        total_misses = sum(int(item["misses"]) for item in self.results)
        self.summary_label.config(text=(
            f"Gemiddeld\n"
            f"Accuracy  {average('accuracy_percent'):.0f}%\n"
            f"Overshoot  {average('overshoot_px'):.1f} px\n"
            f"Correcties  {average('corrections'):.2f}\n"
            f"Reactie  {average('reaction_ms'):.0f} ms\n"
            f"Klikdelay  {average('click_delay_ms'):.0f} ms\n"
            f"Klikhold  {average('click_hold_ms'):.0f} ms\n"
            f"Misklikken  {total_misses}"
        ))

    def _complete(self) -> None:
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status.config(text="Voltooid · opgeslagen", fg=GREEN)
        if self.session_folder:
            summary = {
                "created": datetime.now().isoformat(timespec="seconds"),
                "mode": "human",
                "targets": len(self.results),
                "results": self.results,
            }
            (self.session_folder / "summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
            )

    def _redraw(self) -> None:
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("all")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        for x in range(0, w, 50):
            self.canvas.create_line(x, 0, x, h, fill="#0a1624")
        for y in range(0, h, 50):
            self.canvas.create_line(0, y, w, y, fill="#0a1624")

        if self.running:
            tx, ty = self.target
            r = self.target_radius
            if self.target_shape == "circle":
                self.canvas.create_oval(tx-r, ty-r, tx+r, ty+r, outline=PURPLE, width=3)
            elif self.target_shape == "triangle":
                points = [coordinate for point in _triangle_points(self.target, r) for coordinate in point]
                self.canvas.create_polygon(points, outline=PURPLE, fill="", width=3)
            else:
                self.canvas.create_rectangle(tx-r, ty-r, tx+r, ty+r, outline=PURPLE, width=3)

        if len(self.path) > 1:
            for a, b in zip(self.path, self.path[1:]):
                colour = PURPLE if math.dist((b[1], b[2]), self.target) <= self.target_radius * 1.5 else BLUE
                self.canvas.create_line(a[1], a[2], b[1], b[2], fill=colour, width=2, smooth=True)
        cx, cy = self.cursor
        self.canvas.create_oval(cx-5, cy-5, cx+5, cy+5, fill=CYAN, outline="#ffffff")


def main() -> None:
    root = tk.Tk()
    AimLabApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
