from __future__ import annotations

import json
import math
import random
import time
import tkinter as tk
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

from .core import DATA, list_sessions, load_master_profile
from .human_profile import extract_click_templates, generate_target_path, select_template
from .profile_v2 import build_master_profile

BG = "#070b18"
PANEL = "#10162a"
PANEL_2 = "#151d36"
TEXT = "#f7f8ff"
MUTED = "#919ab5"
PURPLE = "#8a3ffc"
BLUE = "#2478ff"
CYAN = "#26d9ff"
GREEN = "#3ee58a"
RED = "#ff4d6d"
BORDER = "#263154"
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


def _inside_target(x: float, y: float, target: tuple[float, float], radius: float, shape: str) -> bool:
    dx, dy = x - target[0], y - target[1]
    if shape == "circle":
        return dx * dx + dy * dy <= radius * radius
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
        return ActionMetrics(0, 0, 0, 0, 0, reaction_s * 1000, 0, click_delay * 1000, click_hold_s * 1000)
    xy = [(x, y) for _, x, y in path]
    direct = math.dist(xy[0], target)
    travelled = sum(math.dist(a, b) for a, b in zip(xy, xy[1:]))
    distances = [math.dist(point, target) for point in xy]
    first_entry = next((i for i, value in enumerate(distances) if value <= radius), len(distances) - 1)
    overshoot = max(0.0, max(distances[first_entry:], default=radius) - radius)
    corrections = 0
    for a, b, c in zip(distances[first_entry:], distances[first_entry + 1:], distances[first_entry + 2:]):
        if b < a and c > b + 0.8:
            corrections += 1
    return ActionMetrics(
        direct,
        travelled,
        overshoot,
        corrections,
        distances[-1],
        reaction_s * 1000,
        max(0.0, path[-1][0] - path[0][0]) * 1000,
        click_delay * 1000,
        click_hold_s * 1000,
    )


class AimLabApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AI Mouse – Aim Lab")
        self.root.geometry("1120x720")
        self.root.minsize(900, 620)
        self.root.configure(bg=BG)
        self.rng = random.Random()
        self.templates = self._load_templates()
        self.running = False
        self.mode = "human"
        self.after_id: str | None = None
        self.target_total = 20
        self.target_index = 0
        self.target = (500.0, 350.0)
        self.target_radius = 24.0
        self.target_shape = "circle"
        self.previous_target: tuple[float, float] | None = None
        self.path: list[tuple[float, float, float]] = []
        self.path_index = 0
        self.cursor = (110.0, 110.0)
        self.target_spawned_at = 0.0
        self.first_move_at: float | None = None
        self.last_move_at: float | None = None
        self.mouse_down_at: float | None = None
        self.click_delay = 0.0
        self.current_misses = 0
        self.current_resets = 0
        self.results: list[dict] = []
        self.session_folder: Path | None = None
        self.context_var = tk.StringVar(value="Gaming")
        self.size_var = tk.StringVar(value="Mix")
        self.shape_var = tk.StringVar(value="Mix")
        self.distance_var = tk.StringVar(value="Mix")
        self._build()
        self._redraw()

    def _load_templates(self) -> list[dict]:
        profile = load_master_profile()
        stored = profile.get("human_templates") or []
        if stored:
            return list(stored)
        templates: list[dict] = []
        for session in list_sessions():
            if not session.included:
                continue
            for template in extract_click_templates(session.folder / "points.csv", session.label):
                item = template.to_dict()
                item["source_session"] = session.session_id
                item["source_type"] = "recording"
                templates.append(item)
        return sorted(templates, key=lambda item: float(item.get("quality", 0)), reverse=True)[:3000]

    def _button(self, parent, text, command, bg=PANEL_2, **kwargs):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=TEXT, activebackground=bg,
                         activeforeground=TEXT, relief="flat", bd=0, cursor="hand2",
                         font=("Segoe UI", 10, "bold"), **kwargs)

    def _build(self):
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True, padx=18, pady=16)
        header = tk.Frame(shell, bg=BG)
        header.pack(fill="x", pady=(0, 12))
        tk.Label(header, text="Aim Lab", bg=BG, fg=TEXT, font=("Segoe UI", 23, "bold")).pack(side="left")
        self.profile_label = tk.Label(header, text=f"{len(self.templates)} profieltemplates", bg=BG,
                                      fg=GREEN if self.templates else MUTED, font=("Segoe UI", 9, "bold"))
        self.profile_label.pack(side="right")

        controls = tk.Frame(shell, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        controls.pack(fill="x", pady=(0, 10))
        row = tk.Frame(controls, bg=PANEL)
        row.pack(fill="x", padx=14, pady=11)
        self.human_btn = self._button(row, "●  Zelf testen", self.start_human, bg=PURPLE, padx=18, pady=9)
        self.human_btn.pack(side="left")
        self.replay_btn = self._button(row, "▶  Profiel replay", self.start_replay, padx=18, pady=9)
        self.replay_btn.pack(side="left", padx=8)
        self.stop_btn = self._button(row, "■  Stop", self.stop, padx=16, pady=9, state="disabled")
        self.stop_btn.pack(side="left")
        for label, variable, values, width in (
            ("Context", self.context_var, ("Gaming", "Browsing", "Werk", "Precision"), 10),
            ("Grootte", self.size_var, ("Mix", "Klein", "Middel", "Groot"), 8),
            ("Vorm", self.shape_var, ("Mix", "Rond", "Vierkant"), 9),
            ("Afstand", self.distance_var, ("Mix", "Kort", "Middel", "Lang"), 8),
        ):
            tk.Label(row, text=label, bg=PANEL, fg=MUTED).pack(side="left", padx=(12, 4))
            ttk.Combobox(row, textvariable=variable, values=values, state="readonly", width=width).pack(side="left")
        self.status = tk.Label(row, text="Klaar", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold"))
        self.status.pack(side="right")

        body = tk.Frame(shell, bg=BG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=4)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        stage = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        stage.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.canvas = tk.Canvas(stage, bg="#060a15", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True, padx=12, pady=12)
        self.canvas.bind("<Configure>", lambda _e: self._redraw())
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._reset_current_action)

        side = tk.Frame(body, bg=PANEL, width=265, highlightbackground=BORDER, highlightthickness=1)
        side.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        side.grid_propagate(False)
        tk.Label(side, text="Laatste poging", bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(16, 8))
        self.metrics_label = tk.Label(side, text="Klik op Zelf testen.", bg=PANEL, fg=MUTED, justify="left",
                                      anchor="nw", wraplength=225, font=("Segoe UI", 9))
        self.metrics_label.pack(fill="x", padx=16)
        tk.Frame(side, bg=BORDER, height=1).pack(fill="x", padx=16, pady=16)
        tk.Label(side, text="Rechtermuisknop reset de huidige actie.\n\nTargets variëren in grootte, vorm, afstand, hoeken en diagonalen.",
                 bg=PANEL, fg=MUTED, justify="left", wraplength=225, font=("Segoe UI", 9)).pack(anchor="w", padx=16)
        self.summary_label = tk.Label(side, text="", bg=PANEL, fg=TEXT, justify="left", font=("Segoe UI", 9))
        self.summary_label.pack(anchor="w", padx=16, pady=(20, 0))

    def _radius(self) -> float:
        choice = self.size_var.get()
        if choice == "Klein":
            return self.rng.uniform(10, 18)
        if choice == "Middel":
            return self.rng.uniform(24, 38)
        if choice == "Groot":
            return self.rng.uniform(48, 70)
        return self.rng.choice((self.rng.uniform(10, 18), self.rng.uniform(24, 38), self.rng.uniform(48, 70)))

    def _shape(self) -> str:
        choice = self.shape_var.get()
        if choice == "Rond":
            return "circle"
        if choice == "Vierkant":
            return "square"
        return self.rng.choice(("circle", "square"))

    def _candidate_points(self, width: int, height: int, margin: float) -> list[tuple[float, float]]:
        return [
            (margin, margin), (width - margin, margin),
            (margin, height - margin), (width - margin, height - margin),
            (width * 0.5, margin), (width * 0.5, height - margin),
            (margin, height * 0.5), (width - margin, height * 0.5),
            (width * 0.5, height * 0.5),
        ]

    def _new_target(self):
        w, h = max(500, self.canvas.winfo_width()), max(400, self.canvas.winfo_height())
        self.target_radius = self._radius()
        self.target_shape = self._shape()
        margin = self.target_radius + 28
        candidates = self._candidate_points(w, h, margin)
        origin = self.previous_target or self.cursor
        mode = self.distance_var.get()
        if mode == "Mix":
            mode = self.rng.choice(("Kort", "Middel", "Lang", "Lang"))
        if mode == "Kort":
            pool = [p for p in candidates if math.dist(origin, p) < min(w, h) * 0.38]
        elif mode == "Lang":
            pool = [p for p in candidates if math.dist(origin, p) > min(w, h) * 0.70]
        else:
            pool = [p for p in candidates if min(w, h) * 0.35 <= math.dist(origin, p) <= min(w, h) * 0.75]
        base = self.rng.choice(pool or candidates)
        jitter = min(55.0, max(8.0, self.target_radius * 0.7))
        self.target = (
            min(w - margin, max(margin, base[0] + self.rng.uniform(-jitter, jitter))),
            min(h - margin, max(margin, base[1] + self.rng.uniform(-jitter, jitter))),
        )
        self.previous_target = self.target

    def _start_session(self, mode: str):
        self.stop()
        self.mode = mode
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.session_folder = REPORTS / f"{stamp}_{mode}"
        self.session_folder.mkdir(parents=True, exist_ok=False)
        self.results.clear()
        self.target_index = 0
        self.cursor = (110.0, 110.0)
        self.previous_target = None
        self.running = True
        self.human_btn.config(state="disabled")
        self.replay_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status.config(text="Zelf klikken" if mode == "human" else "Profiel replay", fg=GREEN)

    def start_human(self):
        self._start_session("human")
        self._prepare_human_target(new_target=True)

    def start_replay(self):
        self.templates = self._load_templates()
        if not self.templates:
            messagebox.showinfo("Aim Lab", "Maak eerst een muisopname of rond een menselijke Aim Lab-run af.")
            return
        self._start_session("replay")
        self._prepare_replay_target()

    def stop(self):
        self.running = False
        if self.after_id:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None
        if hasattr(self, "human_btn"):
            self.human_btn.config(state="normal")
            self.replay_btn.config(state="normal")
            self.stop_btn.config(state="disabled")

    def _prepare_human_target(self, new_target: bool):
        if not self.running or self.mode != "human":
            return
        if self.target_index >= self.target_total:
            self._complete()
            return
        if new_target:
            self._new_target()
            self.current_misses = 0
            self.current_resets = 0
        self.path = []
        self.first_move_at = None
        self.last_move_at = None
        self.mouse_down_at = None
        self.target_spawned_at = time.perf_counter()
        self._redraw()

    def _reset_current_action(self, _event=None):
        if not self.running or self.mode != "human":
            return "break"
        self.current_resets += 1
        if self.session_folder:
            reset_record = {
                "created": datetime.now().isoformat(timespec="milliseconds"),
                "target_index": self.target_index + 1,
                "target": {"x": self.target[0], "y": self.target[1], "radius": self.target_radius, "shape": self.target_shape},
            }
            with (self.session_folder / "resets.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(reset_record, ensure_ascii=False) + "\n")
        self.status.config(text="Huidige actie gereset", fg=MUTED)
        self._prepare_human_target(new_target=False)
        return "break"

    def _on_motion(self, event):
        if not self.running or self.mode != "human":
            return
        now = time.perf_counter()
        if self.first_move_at is None:
            self.first_move_at = now
        self.last_move_at = now
        self.cursor = (float(event.x), float(event.y))
        self.path.append((now - self.target_spawned_at, float(event.x), float(event.y)))
        self._redraw()

    def _on_press(self, _event):
        if not self.running or self.mode != "human":
            return
        self.mouse_down_at = time.perf_counter()

    def _on_release(self, event):
        if not self.running or self.mode != "human" or self.mouse_down_at is None:
            return
        released_at = time.perf_counter()
        pressed_at = self.mouse_down_at
        self.mouse_down_at = None
        if not _inside_target(event.x, event.y, self.target, self.target_radius, self.target_shape):
            self.current_misses += 1
            self.status.config(text=f"Mis ({self.current_misses}) – probeer opnieuw of rechtsklik reset", fg=RED)
            return
        if not self.path:
            self.path = [(0.0, float(event.x), float(event.y)), (0.001, float(event.x), float(event.y))]
        click_delay = max(0.0, pressed_at - (self.last_move_at or pressed_at))
        reaction = max(0.0, (self.first_move_at or pressed_at) - self.target_spawned_at)
        hold = max(0.0, released_at - pressed_at)
        self._finish_human_action(click_delay, reaction, hold)

    def _finish_human_action(self, click_delay: float, reaction: float, hold: float):
        metrics = path_metrics(self.path, self.target, self.target_radius, click_delay, reaction, hold)
        self._save_action(metrics, source_session="human")
        self.cursor = (self.path[-1][1], self.path[-1][2])
        self.target_index += 1
        self.status.config(text="Raak", fg=GREEN)
        self.after_id = self.root.after(220, lambda: self._prepare_human_target(new_target=True))

    def _prepare_replay_target(self):
        if not self.running or self.mode != "replay":
            return
        if self.target_index >= self.target_total:
            self._complete()
            return
        self._new_target()
        template = select_template(self.templates, math.dist(self.cursor, self.target), self.context_var.get(), self.rng)
        if template is None:
            self.stop()
            return
        self.current_template = template
        self.path, self.click_delay = generate_target_path(template, self.cursor, self.target, self.rng, self.target_radius)
        self.path_index = 0
        self._redraw()
        self._animate_replay()

    def _animate_replay(self):
        if not self.running or self.mode != "replay":
            return
        if self.path_index >= len(self.path):
            self.after_id = self.root.after(max(1, int(self.click_delay * 1000)), self._finish_replay_action)
            return
        _, x, y = self.path[self.path_index]
        self.cursor = (x, y)
        self.path_index += 1
        self._redraw()
        delay = 12
        if self.path_index < len(self.path):
            delay = max(4, min(60, int((self.path[self.path_index][0] - self.path[self.path_index - 1][0]) * 1000)))
        self.after_id = self.root.after(delay, self._animate_replay)

    def _finish_replay_action(self):
        metrics = path_metrics(self.path, self.target, self.target_radius, self.click_delay)
        self._save_action(metrics, source_session=self.current_template.get("source_session", ""))
        self.cursor = (self.path[-1][1], self.path[-1][2])
        self.target_index += 1
        self.after_id = self.root.after(220, self._prepare_replay_target)

    def _save_action(self, metrics: ActionMetrics, source_session: str):
        record = {
            "target_index": self.target_index + 1,
            "mode": self.mode,
            "context": self.context_var.get(),
            "target": {"x": self.target[0], "y": self.target[1], "radius": self.target_radius, "shape": self.target_shape},
            "distance_mode": self.distance_var.get(),
            "source_session": source_session,
            "misses": self.current_misses if self.mode == "human" else 0,
            "resets": self.current_resets if self.mode == "human" else 0,
            "metrics": asdict(metrics),
            "path": [[round(t, 6), round(x, 3), round(y, 3)] for t, x, y in self.path],
        }
        self.results.append(record)
        if self.session_folder:
            with (self.session_folder / "actions.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.metrics_label.config(text=(
            f"Target {self.target_index + 1}/{self.target_total}\n\n"
            f"Afstand: {metrics.direct_distance:.0f} px\n"
            f"Werkelijk pad: {metrics.travelled_distance:.0f} px\n"
            f"Reactie: {metrics.reaction_ms:.0f} ms\n"
            f"Beweegtijd: {metrics.movement_ms:.0f} ms\n"
            f"Overshoot: {metrics.overshoot_px:.1f} px\n"
            f"Correcties: {metrics.corrections}\n"
            f"Misklikken: {record['misses']}\n"
            f"Klikdelay: {metrics.click_delay_ms:.0f} ms\n"
            f"Klikhold: {metrics.click_hold_ms:.0f} ms"
        ))
        self._update_summary()

    def _complete(self):
        self.running = False
        self.human_btn.config(state="normal")
        self.replay_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        profile_result = None
        profile_error = None
        if self.mode == "human" and self.results:
            try:
                profile_result = build_master_profile(list_sessions())
                self.templates = list(profile_result.get("human_templates") or [])
                self.profile_label.config(text=f"{len(self.templates)} profieltemplates", fg=GREEN)
            except Exception as exc:
                profile_error = str(exc)
        self.status.config(text="Voltooid · profiel bijgewerkt" if profile_result else "Voltooid", fg=GREEN)
        if self.session_folder:
            summary = {
                "created": datetime.now().isoformat(timespec="seconds"),
                "mode": self.mode,
                "context": self.context_var.get(),
                "targets": len(self.results),
                "size_mode": self.size_var.get(),
                "shape_mode": self.shape_var.get(),
                "distance_mode": self.distance_var.get(),
                "master_profile_updated": profile_result is not None,
                "master_profile_error": profile_error,
                "master_profile_template_count": len(self.templates) if profile_result else None,
                "results": self.results,
            }
            (self.session_folder / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    def _update_summary(self):
        if not self.results:
            return
        metrics = [item["metrics"] for item in self.results]
        self.summary_label.config(text=(
            f"Gemiddeld\n"
            f"Reactie  {sum(m['reaction_ms'] for m in metrics)/len(metrics):.0f} ms\n"
            f"Beweging  {sum(m['movement_ms'] for m in metrics)/len(metrics):.0f} ms\n"
            f"Overshoot  {sum(m['overshoot_px'] for m in metrics)/len(metrics):.1f} px\n"
            f"Correcties  {sum(m['corrections'] for m in metrics)/len(metrics):.2f}"
        ))

    def _redraw(self):
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("all")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        for x in range(0, w, 50):
            self.canvas.create_line(x, 0, x, h, fill="#0b1223")
        for y in range(0, h, 50):
            self.canvas.create_line(0, y, w, y, fill="#0b1223")
        tx, ty = self.target
        r = self.target_radius
        outline = PURPLE if self.running else "#43506c"
        if self.target_shape == "circle":
            self.canvas.create_oval(tx-r, ty-r, tx+r, ty+r, outline=outline, width=3)
        else:
            self.canvas.create_rectangle(tx-r, ty-r, tx+r, ty+r, outline=outline, width=3)
        shown_path = self.path if self.mode == "human" else self.path[:self.path_index]
        if len(shown_path) > 1:
            for a, b in zip(shown_path, shown_path[1:]):
                colour = PURPLE if math.dist((b[1], b[2]), self.target) <= r * 1.5 else BLUE
                self.canvas.create_line(a[1], a[2], b[1], b[2], fill=colour, width=3, smooth=True)
        cx, cy = self.cursor
        self.canvas.create_oval(cx-6, cy-6, cx+6, cy+6, fill=CYAN, outline="#ffffff")
        self.canvas.create_text(18, 16, text=("JIJ KLIKT" if self.mode == "human" else "PROFIEL REPLAY") if self.running else "KLAAR",
                                fill=MUTED, anchor="nw", font=("Segoe UI", 9, "bold"))


def main():
    root = tk.Tk()
    AimLabApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
