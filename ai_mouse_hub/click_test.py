from __future__ import annotations

import json
import math
import random
import time
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

from .core import DATA, list_sessions
from .human_profile import extract_click_templates, generate_target_path, select_template

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
    duration_ms: float
    click_delay_ms: float


def path_metrics(path: list[tuple[float, float, float]], target: tuple[float, float], radius: float, click_delay: float) -> ActionMetrics:
    if len(path) < 2:
        return ActionMetrics(0, 0, 0, 0, 0, 0, click_delay * 1000)
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
    return ActionMetrics(direct, travelled, overshoot, corrections, distances[-1], path[-1][0] * 1000, click_delay * 1000)


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
        self.after_id: str | None = None
        self.target_total = 20
        self.target_index = 0
        self.cursor = (110.0, 110.0)
        self.target = (500.0, 350.0)
        self.target_radius = 24.0
        self.path: list[tuple[float, float, float]] = []
        self.path_index = 0
        self.click_delay = 0.06
        self.action_started = 0.0
        self.results: list[dict] = []
        self.session_folder: Path | None = None
        self.context_var = tk.StringVar(value="Gaming")
        self.size_var = tk.StringVar(value="Mix")
        self._build()
        self._redraw()

    def _load_templates(self) -> list[dict]:
        templates: list[dict] = []
        for session in list_sessions():
            if not session.included:
                continue
            for template in extract_click_templates(session.folder / "points.csv", session.label):
                item = template.to_dict()
                item["source_session"] = session.session_id
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
        self.profile_label = tk.Label(header, text=f"{len(self.templates)} menselijke templates", bg=BG,
                                      fg=GREEN if self.templates else RED, font=("Segoe UI", 9, "bold"))
        self.profile_label.pack(side="right")

        controls = tk.Frame(shell, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        controls.pack(fill="x", pady=(0, 10))
        row = tk.Frame(controls, bg=PANEL)
        row.pack(fill="x", padx=14, pady=11)
        self.start_btn = self._button(row, "▶  Start", self.start, bg=PURPLE, padx=22, pady=9)
        self.start_btn.pack(side="left")
        self.stop_btn = self._button(row, "■  Stop", self.stop, padx=18, pady=9, state="disabled")
        self.stop_btn.pack(side="left", padx=8)
        tk.Label(row, text="Profiel", bg=PANEL, fg=MUTED).pack(side="left", padx=(18, 6))
        ttk.Combobox(row, textvariable=self.context_var, values=("Gaming", "Browsing", "Werk", "Precision"),
                     state="readonly", width=12).pack(side="left")
        tk.Label(row, text="Targets", bg=PANEL, fg=MUTED).pack(side="left", padx=(18, 6))
        ttk.Combobox(row, textvariable=self.size_var, values=("Mix", "Klein", "Middel", "Groot"),
                     state="readonly", width=10).pack(side="left")
        self.status = tk.Label(row, text="Klaar", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold"))
        self.status.pack(side="right")

        body = tk.Frame(shell, bg=BG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=4)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        stage = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        stage.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.canvas = tk.Canvas(stage, bg="#060a15", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=12)
        self.canvas.bind("<Configure>", lambda _e: self._redraw())

        side = tk.Frame(body, bg=PANEL, width=265, highlightbackground=BORDER, highlightthickness=1)
        side.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        side.grid_propagate(False)
        tk.Label(side, text="Laatste beweging", bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(16, 8))
        self.metrics_label = tk.Label(side, text="Start de test.", bg=PANEL, fg=MUTED, justify="left",
                                      anchor="nw", wraplength=225, font=("Segoe UI", 9))
        self.metrics_label.pack(fill="x", padx=16)
        tk.Frame(side, bg=BORDER, height=1).pack(fill="x", padx=16, pady=16)
        tk.Label(side, text="Blauw  beweging\nPaars  overshoot / correctie\nGroen  virtueel klikmoment",
                 bg=PANEL, fg=MUTED, justify="left", font=("Segoe UI", 9)).pack(anchor="w", padx=16)
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

    def _new_target(self):
        w, h = max(500, self.canvas.winfo_width()), max(400, self.canvas.winfo_height())
        self.target_radius = self._radius()
        margin = self.target_radius + 45
        self.target = (self.rng.uniform(margin, w - margin), self.rng.uniform(margin, h - margin))

    def start(self):
        if not self.templates:
            messagebox.showinfo("Aim Lab", "Maak eerst een muisopname met echte clicks.")
            return
        self.stop()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.session_folder = REPORTS / stamp
        self.session_folder.mkdir(parents=True, exist_ok=False)
        self.results.clear()
        self.target_index = 0
        self.cursor = (110.0, 110.0)
        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status.config(text="Test actief", fg=GREEN)
        self._prepare_action()

    def stop(self):
        self.running = False
        if self.after_id:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None
        if hasattr(self, "start_btn"):
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")

    def _prepare_action(self):
        if not self.running:
            return
        if self.target_index >= self.target_total:
            self.running = False
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.status.config(text="Voltooid", fg=GREEN)
            self._save_summary()
            return
        self._new_target()
        distance = math.dist(self.cursor, self.target)
        template = select_template(self.templates, distance, self.context_var.get(), self.rng)
        if template is None:
            self.stop()
            return
        self.path, self.click_delay = generate_target_path(template, self.cursor, self.target, self.rng, self.target_radius)
        self.path_index = 0
        self.action_started = time.perf_counter()
        self.current_template = template
        self._redraw()
        self._animate_step()

    def _animate_step(self):
        if not self.running:
            return
        if self.path_index >= len(self.path):
            self.after_id = self.root.after(max(1, int(self.click_delay * 1000)), self._finish_action)
            return
        self.path_index += 1
        self._redraw()
        delay = 12
        if self.path_index < len(self.path):
            previous_t = self.path[self.path_index - 1][0]
            next_t = self.path[self.path_index][0]
            delay = max(4, min(60, int((next_t - previous_t) * 1000)))
        self.after_id = self.root.after(delay, self._animate_step)

    def _finish_action(self):
        metrics = path_metrics(self.path, self.target, self.target_radius, self.click_delay)
        record = {
            "target_index": self.target_index + 1,
            "context": self.context_var.get(),
            "target": {"x": self.target[0], "y": self.target[1], "radius": self.target_radius},
            "source_session": self.current_template.get("source_session", ""),
            "template": {key: self.current_template.get(key) for key in ("duration_s", "direct_distance", "curve_ratio", "overshoot_ratio", "corrections", "quality")},
            "metrics": metrics.__dict__,
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
            f"Overshoot: {metrics.overshoot_px:.1f} px\n"
            f"Correcties: {metrics.corrections}\n"
            f"Eindoffset: {metrics.final_offset_px:.1f} px\n"
            f"Beweegtijd: {metrics.duration_ms:.0f} ms\n"
            f"Klikdelay: {metrics.click_delay_ms:.0f} ms"
        ))
        self.cursor = (self.path[-1][1], self.path[-1][2])
        self.target_index += 1
        self._update_summary()
        self.after_id = self.root.after(260, self._prepare_action)

    def _update_summary(self):
        if not self.results:
            return
        metrics = [item["metrics"] for item in self.results]
        self.summary_label.config(text=(
            f"Gemiddeld\n"
            f"Overshoot  {sum(m['overshoot_px'] for m in metrics)/len(metrics):.1f} px\n"
            f"Correcties  {sum(m['corrections'] for m in metrics)/len(metrics):.2f}\n"
            f"Eindoffset  {sum(m['final_offset_px'] for m in metrics)/len(metrics):.1f} px"
        ))

    def _save_summary(self):
        if not self.session_folder:
            return
        summary = {
            "created": datetime.now().isoformat(timespec="seconds"),
            "context": self.context_var.get(),
            "target_mode": self.size_var.get(),
            "actions": len(self.results),
            "template_count_available": len(self.templates),
            "privacy": {"virtual_cursor_only": True, "external_apps_controlled": False, "keyboard_recorded": False},
        }
        (self.session_folder / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    def _redraw(self):
        self.canvas.delete("all")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        for x in range(0, w, 52):
            self.canvas.create_line(x, 0, x, h, fill="#0d1426")
        for y in range(0, h, 52):
            self.canvas.create_line(0, y, w, y, fill="#0d1426")
        tx, ty = self.target
        r = self.target_radius
        self.canvas.create_oval(tx-r, ty-r, tx+r, ty+r, fill="#251744", outline=PURPLE, width=2)
        self.canvas.create_oval(tx-3, ty-3, tx+3, ty+3, fill=TEXT, outline="")
        visible = self.path[:self.path_index]
        if visible:
            distances = [math.dist((x, y), self.target) for _, x, y in visible]
            first_entry = next((i for i, value in enumerate(distances) if value <= r), len(visible))
            for index in range(1, len(visible)):
                _, x1, y1 = visible[index - 1]
                _, x2, y2 = visible[index]
                colour = BLUE if index < first_entry else PURPLE
                self.canvas.create_line(x1, y1, x2, y2, fill=colour, width=3, smooth=True)
            _, cx, cy = visible[-1]
        else:
            cx, cy = self.cursor
        self.canvas.create_oval(cx-8, cy-8, cx+8, cy+8, fill=CYAN, outline="#ffffff")
        if self.path_index >= len(self.path) and self.path:
            self.canvas.create_oval(cx-13, cy-13, cx+13, cy+13, outline=GREEN, width=3)


def main():
    root = tk.Tk()
    AimLabApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
