from __future__ import annotations

import json
import math
import random
import statistics
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

from .core import DATA, load_master_profile
from .human_profile import generate_target_path

BG = "#070b18"
PANEL = "#10162a"
TEXT = "#f7f8ff"
MUTED = "#919ab5"
PURPLE = "#8a3ffc"
BLUE = "#2478ff"
GREEN = "#3ee58a"
YELLOW = "#f4c95d"
RED = "#ff4d6d"
BORDER = "#263154"
REPORTS = DATA / "human_score_lab"
REPORTS.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class RunMetrics:
    duration_ms: float
    direct_distance: float
    travelled_distance: float
    curve_ratio: float
    peak_speed: float
    overshoot_ratio: float
    corrections: int
    click_delay_ms: float
    final_offset_ratio: float
    fingerprint: str


def _mean(values: list[float], default: float = 0.0) -> float:
    return statistics.fmean(values) if values else default


def _std(values: list[float], default: float = 1.0) -> float:
    return max(1e-6, statistics.pstdev(values)) if len(values) > 1 else default


def _score_distribution(value: float, baseline: list[float], tolerance: float = 2.5) -> float:
    if not baseline:
        return 55.0
    z = abs(value - _mean(baseline)) / _std(baseline, max(1.0, abs(_mean(baseline)) * 0.18))
    return max(0.0, min(100.0, 100.0 * (1.0 - z / tolerance)))


def _fingerprint(path: list[tuple[float, float, float]]) -> str:
    if len(path) < 2:
        return "empty"
    points = []
    stride = max(1, len(path) // 16)
    start_x, start_y = path[0][1], path[0][2]
    end_x, end_y = path[-1][1], path[-1][2]
    scale = max(1.0, math.dist((start_x, start_y), (end_x, end_y)))
    for _, x, y in path[::stride][:16]:
        points.append(f"{round((x-start_x)/scale, 2)}:{round((y-start_y)/scale, 2)}")
    return "|".join(points)


def measure_run(path: list[tuple[float, float, float]], target: tuple[float, float], radius: float, click_delay: float) -> RunMetrics:
    if len(path) < 2:
        return RunMetrics(0, 0, 0, 0, 0, 0, 0, click_delay * 1000, 0, "empty")
    xy = [(x, y) for _, x, y in path]
    direct = max(1.0, math.dist(xy[0], target))
    travelled = sum(math.dist(a, b) for a, b in zip(xy, xy[1:]))
    speeds = []
    for a, b in zip(path, path[1:]):
        dt = max(0.001, b[0] - a[0])
        speeds.append(math.dist((a[1], a[2]), (b[1], b[2])) / dt)
    distances = [math.dist(point, target) for point in xy]
    first_entry = next((i for i, d in enumerate(distances) if d <= radius), len(distances) - 1)
    overshoot = max(0.0, max(distances[first_entry:], default=radius) - radius) / direct
    corrections = 0
    tail = distances[first_entry:]
    for a, b, c in zip(tail, tail[1:], tail[2:]):
        if b < a and c > b + max(0.8, radius * 0.025):
            corrections += 1
    return RunMetrics(
        duration_ms=max(0.0, path[-1][0] - path[0][0]) * 1000,
        direct_distance=direct,
        travelled_distance=travelled,
        curve_ratio=travelled / direct,
        peak_speed=max(speeds, default=0.0),
        overshoot_ratio=overshoot,
        corrections=corrections,
        click_delay_ms=click_delay * 1000,
        final_offset_ratio=distances[-1] / max(1.0, radius),
        fingerprint=_fingerprint(path),
    )


def baseline_from_templates(templates: list[dict]) -> dict[str, list[float]]:
    baseline = {
        "duration_ms": [], "curve_ratio": [], "overshoot_ratio": [],
        "corrections": [], "click_delay_ms": [], "direct_distance": [],
    }
    for item in templates:
        baseline["duration_ms"].append(float(item.get("duration_s", 0.45)) * 1000)
        baseline["curve_ratio"].append(float(item.get("curve_ratio", 1.12)))
        baseline["overshoot_ratio"].append(float(item.get("overshoot_ratio", 0.0)))
        baseline["corrections"].append(float(item.get("corrections", 0)))
        baseline["click_delay_ms"].append(float(item.get("click_delay_s", 0.07)) * 1000)
        baseline["direct_distance"].append(float(item.get("direct_distance", 300.0)))
    return baseline


def simulate_profile(profile: dict, runs: int = 100, seed: int | None = None) -> dict:
    templates = list(profile.get("templates") or [])
    if not templates:
        raise ValueError("Geen profieltemplates gevonden. Bouw eerst het masterprofiel.")
    runs = max(10, min(1000, int(runs)))
    rng = random.Random(seed)
    baseline = baseline_from_templates(templates)
    generated: list[RunMetrics] = []
    run_records: list[dict] = []
    fingerprints: dict[str, int] = {}

    corners = [(80.0, 80.0), (1040.0, 80.0), (80.0, 620.0), (1040.0, 620.0)]
    cursor = (560.0, 350.0)
    for index in range(runs):
        radius = rng.choice((rng.uniform(10, 18), rng.uniform(24, 38), rng.uniform(48, 70)))
        if index % 3 == 0:
            target = corners[index % len(corners)]
        else:
            target = (rng.uniform(radius + 35, 1120 - radius - 35), rng.uniform(radius + 35, 700 - radius - 35))
        distance = math.dist(cursor, target)
        pool = sorted(templates, key=lambda item: abs(float(item.get("direct_distance", distance)) - distance))
        pool = pool[:max(5, min(len(pool), len(pool) // 3 or 5))]
        template = rng.choice(pool)
        path, click_delay = generate_target_path(template, cursor, target, rng, radius)
        metrics = measure_run(path, target, radius, click_delay)
        generated.append(metrics)
        fingerprints[metrics.fingerprint] = fingerprints.get(metrics.fingerprint, 0) + 1
        match_parts = [
            _score_distribution(metrics.duration_ms, baseline["duration_ms"]),
            _score_distribution(metrics.curve_ratio, baseline["curve_ratio"]),
            _score_distribution(metrics.overshoot_ratio, baseline["overshoot_ratio"]),
            _score_distribution(float(metrics.corrections), baseline["corrections"]),
            _score_distribution(metrics.click_delay_ms, baseline["click_delay_ms"]),
        ]
        run_score = round(_mean(match_parts), 1)
        run_records.append({"run": index + 1, "score": run_score, "metrics": metrics.__dict__})
        cursor = (path[-1][1], path[-1][2])

    duration_scores = [_score_distribution(m.duration_ms, baseline["duration_ms"]) for m in generated]
    curve_scores = [_score_distribution(m.curve_ratio, baseline["curve_ratio"]) for m in generated]
    overshoot_scores = [_score_distribution(m.overshoot_ratio, baseline["overshoot_ratio"]) for m in generated]
    correction_scores = [_score_distribution(float(m.corrections), baseline["corrections"]) for m in generated]
    click_scores = [_score_distribution(m.click_delay_ms, baseline["click_delay_ms"]) for m in generated]
    duplicates = sum(count - 1 for count in fingerprints.values() if count > 1)
    repetition_score = max(0.0, 100.0 * (1.0 - duplicates / runs))

    generated_durations = [m.duration_ms for m in generated]
    generated_curves = [m.curve_ratio for m in generated]
    variability = min(100.0, 50.0 + 25.0 * min(1.0, _std(generated_durations) / max(1.0, _mean(generated_durations) * 0.18))
                      + 25.0 * min(1.0, _std(generated_curves) / max(0.01, _mean(generated_curves) * 0.08)))
    profile_match = _mean(curve_scores + duration_scores)
    timing_match = _mean(duration_scores + click_scores)
    target_behaviour = _mean(overshoot_scores + correction_scores)
    overall = round(profile_match * 0.30 + timing_match * 0.20 + target_behaviour * 0.20 + variability * 0.15 + repetition_score * 0.15, 1)

    sample_count = int(profile.get("source_count", 0)) or len(templates)
    aim_lab_count = int(profile.get("aim_lab_template_count", 0))
    confidence = round(min(100.0, 18.0 + math.log2(max(2, sample_count)) * 8.0 + min(30.0, aim_lab_count * 0.9)), 1)

    result = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "runs": runs,
        "scores": {
            "hesse_profile_score": overall,
            "human_profile_match": round(profile_match, 1),
            "timing_match": round(timing_match, 1),
            "natural_variation": round(variability, 1),
            "target_behaviour": round(target_behaviour, 1),
            "repetition_control": round(repetition_score, 1),
            "data_confidence": confidence,
        },
        "data": {
            "templates": len(templates),
            "source_count": sample_count,
            "aim_lab_templates": aim_lab_count,
            "duplicate_fingerprints": duplicates,
        },
        "interpretation": (
            "Sterke menselijke profielmatch" if overall >= 80 else
            "Redelijke profielmatch" if overall >= 65 else
            "Gemengd of te voorspelbaar" if overall >= 45 else
            "Duidelijk afwijkend van huidige baseline"
        ),
        "confidence_label": "goed" if confidence >= 75 else "voorlopig" if confidence >= 40 else "laag",
        "run_results": run_records,
    }
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = REPORTS / stamp
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "report.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


class HumanScoreLabApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AI Mouse – Human Score Lab")
        self.root.geometry("980x680")
        self.root.minsize(820, 600)
        self.root.configure(bg=BG)
        self.result: dict | None = None
        self._build()

    def _button(self, parent, text, command, bg=PURPLE, **kwargs):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=TEXT, activebackground=bg,
                         activeforeground=TEXT, relief="flat", bd=0, cursor="hand2",
                         font=("Segoe UI", 10, "bold"), **kwargs)

    def _build(self):
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True, padx=22, pady=20)
        tk.Label(shell, text="Human Score Lab", bg=BG, fg=TEXT, font=("Segoe UI", 24, "bold")).pack(anchor="w")
        tk.Label(shell, text="Simuleer 100 nieuwe profielruns en vergelijk ze met jouw huidige masterprofiel.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 16))

        controls = tk.Frame(shell, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        controls.pack(fill="x")
        row = tk.Frame(controls, bg=PANEL)
        row.pack(fill="x", padx=14, pady=12)
        tk.Label(row, text="Aantal runs", bg=PANEL, fg=MUTED).pack(side="left")
        self.runs_var = tk.IntVar(value=100)
        tk.Spinbox(row, from_=10, to=1000, textvariable=self.runs_var, width=7, bg="#151d36", fg=TEXT,
                   buttonbackground="#151d36", relief="flat").pack(side="left", padx=8)
        self.start_btn = self._button(row, "Start profieltest", self.run_test, padx=22, pady=9)
        self.start_btn.pack(side="left", padx=(10, 0))
        self.status = tk.Label(row, text="Klaar", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold"))
        self.status.pack(side="right")

        body = tk.Frame(shell, bg=BG)
        body.pack(fill="both", expand=True, pady=(12, 0))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        score_panel = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        score_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tk.Label(score_panel, text="Hesse Profile Score", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 11, "bold")).pack(pady=(22, 6))
        self.main_score = tk.Label(score_panel, text="—", bg=PANEL, fg=GREEN, font=("Segoe UI", 42, "bold"))
        self.main_score.pack()
        self.interpretation = tk.Label(score_panel, text="Nog niet getest", bg=PANEL, fg=TEXT,
                                       font=("Segoe UI", 11, "bold"))
        self.interpretation.pack(pady=(0, 18))
        self.score_text = tk.Label(score_panel, text="", bg=PANEL, fg=MUTED, justify="left",
                                   anchor="nw", font=("Segoe UI", 10))
        self.score_text.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        detail_panel = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        detail_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        tk.Label(detail_panel, text="Wat wordt getest?", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(20, 10))
        detail = (
            "• profielmatch van timing en kromming\n"
            "• overshoot en mini-correcties\n"
            "• clickdelay en targetgedrag\n"
            "• natuurlijke spreiding tussen runs\n"
            "• herhaling van padfingerprints\n\n"
            "De uitslag is een profielvergelijking, geen algemene\n"
            "of absolute AI-detector."
        )
        tk.Label(detail_panel, text=detail, bg=PANEL, fg=MUTED, justify="left",
                 font=("Segoe UI", 10)).pack(anchor="w", padx=20)
        self.data_text = tk.Label(detail_panel, text="", bg=PANEL, fg=TEXT, justify="left",
                                  font=("Segoe UI", 10))
        self.data_text.pack(anchor="w", padx=20, pady=(28, 0))

    def run_test(self):
        profile = load_master_profile()
        if not profile:
            messagebox.showwarning("Human Score Lab", "Bouw eerst een masterprofiel.")
            return
        self.start_btn.config(state="disabled")
        self.status.config(text="100 runs uitvoeren…", fg=YELLOW)
        self.root.update_idletasks()
        try:
            self.result = simulate_profile(profile, self.runs_var.get())
        except Exception as exc:
            self.start_btn.config(state="normal")
            self.status.config(text="Fout", fg=RED)
            messagebox.showerror("Human Score Lab", str(exc))
            return
        self.start_btn.config(state="normal")
        self.status.config(text="Voltooid", fg=GREEN)
        scores = self.result["scores"]
        self.main_score.config(text=f"{scores['hesse_profile_score']:.0f} / 100")
        self.interpretation.config(text=self.result["interpretation"])
        self.score_text.config(text=(
            f"Profielmatch          {scores['human_profile_match']:.0f} / 100\n"
            f"Timingmatch           {scores['timing_match']:.0f} / 100\n"
            f"Natuurlijke variatie  {scores['natural_variation']:.0f} / 100\n"
            f"Targetgedrag          {scores['target_behaviour']:.0f} / 100\n"
            f"Herhalingscontrole    {scores['repetition_control']:.0f} / 100\n\n"
            f"Datavertrouwen        {scores['data_confidence']:.0f} / 100\n"
            f"Confidence            {self.result['confidence_label']}"
        ))
        data = self.result["data"]
        self.data_text.config(text=(
            f"Gebruikte templates: {data['templates']}\n"
            f"Bronnen: {data['source_count']}\n"
            f"Aim Lab-templates: {data['aim_lab_templates']}\n"
            f"Dubbele fingerprints: {data['duplicate_fingerprints']}"
        ))


def main():
    root = tk.Tk()
    HumanScoreLabApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
