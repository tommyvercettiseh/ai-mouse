from __future__ import annotations

import json
import math
import random
import statistics
import tkinter as tk
from datetime import datetime
from tkinter import messagebox

from .core import DATA, list_sessions, load_master_profile
from .human_profile import extract_click_templates, generate_target_path

BG = "#070b18"
PANEL = "#10162a"
TEXT = "#f7f8ff"
MUTED = "#919ab5"
PURPLE = "#8a3ffc"
GREEN = "#3ee58a"
YELLOW = "#f4c95d"
RED = "#ff4d6d"
BORDER = "#263154"
REPORTS = DATA / "human_score_lab"
REPORTS.mkdir(parents=True, exist_ok=True)


def _mean(values: list[float], default: float = 0.0) -> float:
    return statistics.fmean(values) if values else default


def _std(values: list[float], default: float = 1.0) -> float:
    return max(1e-6, statistics.pstdev(values)) if len(values) > 1 else default


def _score(value: float, baseline: list[float], tolerance: float = 2.8) -> float:
    if not baseline:
        return 50.0
    mean = _mean(baseline)
    spread = _std(baseline, max(1.0, abs(mean) * 0.20))
    z = abs(value - mean) / spread
    return max(0.0, min(100.0, 100.0 * (1.0 - z / tolerance)))


def _is_point(value: object) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) >= 2
        and all(isinstance(part, (int, float)) for part in value[:2])
    )


def _is_legacy_path(value: object) -> bool:
    return isinstance(value, list) and len(value) >= 2 and all(_is_point(point) for point in value)


def _is_template(item: object) -> bool:
    return isinstance(item, dict) and isinstance(item.get("points"), list) and len(item["points"]) >= 2


def _legacy_to_template(path: list, index: int, profile: dict) -> dict | None:
    """Convert old master-profile XY paths to the current target-template format."""
    points = [(float(point[0]), float(point[1])) for point in path if _is_point(point)]
    if len(points) < 2:
        return None

    start = points[0]
    end = points[-1]
    dx, dy = end[0] - start[0], end[1] - start[1]
    direct = math.hypot(dx, dy)
    if direct < 1e-6:
        return None

    ux, uy = dx / direct, dy / direct
    px, py = -uy, ux
    travelled = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
    count = len(points)
    local = []
    along_values = []
    distances_to_end = []
    for point_index, (x, y) in enumerate(points):
        rel_x, rel_y = x - start[0], y - start[1]
        along = (rel_x * ux + rel_y * uy) / direct
        perpendicular = (rel_x * px + rel_y * py) / direct
        local.append([point_index / max(1, count - 1), along, perpendicular])
        along_values.append(along)
        distances_to_end.append(math.dist((x, y), end) / direct)

    corrections = 0
    for a, b, c in zip(distances_to_end, distances_to_end[1:], distances_to_end[2:]):
        if b < a and c > b + 0.002:
            corrections += 1

    features = profile.get("features") if isinstance(profile.get("features"), dict) else {}
    step_mean = features.get("step_mean") if isinstance(features.get("step_mean"), dict) else {}
    estimated_duration = max(0.14, min(1.8, 0.18 + count * 0.008 + float(step_mean.get("mean", 0.0)) * 0.015))

    return {
        "points": local,
        "duration_s": estimated_duration,
        "click_delay_s": 0.07,
        "direct_distance": direct,
        "travelled_distance": travelled,
        "curve_ratio": travelled / direct,
        "overshoot_ratio": max(0.0, max(along_values) - 1.0),
        "corrections": corrections,
        "context": "Legacy profile",
        "quality": 0.65,
        "source_session": f"legacy_master_{index}",
        "source_type": "legacy_master_profile",
    }


def _collect_nested_templates(value: object, out: list[dict], profile: dict, counter: list[int]) -> None:
    if _is_template(value):
        out.append(value)
        return
    if _is_legacy_path(value):
        converted = _legacy_to_template(value, counter[0], profile)
        counter[0] += 1
        if converted:
            out.append(converted)
        return
    if isinstance(value, list):
        for item in value:
            _collect_nested_templates(item, out, profile, counter)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key in {"run_results", "results", "scores"}:
                continue
            _collect_nested_templates(item, out, profile, counter)


def load_usable_templates() -> tuple[list[dict], dict]:
    profile = load_master_profile() or {}
    templates: list[dict] = []
    _collect_nested_templates(profile, templates, profile, [0])
    profile_count = len(templates)
    legacy_count = sum(1 for item in templates if item.get("source_type") == "legacy_master_profile")

    recording_templates = 0
    if len(templates) < 5:
        for session in list_sessions():
            if not session.included:
                continue
            for template in extract_click_templates(session.folder / "points.csv", session.label):
                item = template.to_dict()
                item["source_session"] = session.session_id
                item["source_type"] = "recording_fallback"
                templates.append(item)
                recording_templates += 1

    unique: dict[tuple, dict] = {}
    for item in templates:
        points = item.get("points") or []
        key = (
            str(item.get("source_session", "")),
            round(float(item.get("direct_distance", 0.0)), 1),
            round(float(item.get("duration_s", 0.0)), 3),
            len(points),
        )
        unique[key] = item
    templates = list(unique.values())

    aim_lab_count = int(profile.get("aim_lab_template_count", 0) or 0)
    return templates, {
        "profile_templates": profile_count,
        "legacy_templates": legacy_count,
        "recording_fallback_templates": recording_templates,
        "usable_templates": len(templates),
        "aim_lab_templates": aim_lab_count,
        "profile_found": bool(profile),
    }


def _measure(path: list[tuple[float, float, float]], target: tuple[float, float], radius: float, click_delay: float) -> dict:
    xy = [(x, y) for _, x, y in path]
    direct = max(1.0, math.dist(xy[0], target))
    travelled = sum(math.dist(a, b) for a, b in zip(xy, xy[1:]))
    speeds = []
    for a, b in zip(path, path[1:]):
        dt = max(0.001, b[0] - a[0])
        speeds.append(math.dist((a[1], a[2]), (b[1], b[2])) / dt)
    distances = [math.dist(point, target) for point in xy]
    first_entry = next((i for i, d in enumerate(distances) if d <= radius), len(distances) - 1)
    tail = distances[first_entry:]
    corrections = sum(1 for a, b, c in zip(tail, tail[1:], tail[2:]) if b < a and c > b + max(0.8, radius * 0.025))
    return {
        "duration_ms": max(0.0, path[-1][0] - path[0][0]) * 1000,
        "curve_ratio": travelled / direct,
        "overshoot_ratio": max(0.0, max(tail, default=radius) - radius) / direct,
        "corrections": float(corrections),
        "click_delay_ms": click_delay * 1000,
        "peak_speed": max(speeds, default=0.0),
    }


def run_simulation(runs: int) -> dict:
    templates, info = load_usable_templates()
    if len(templates) < 2:
        raise ValueError(
            "Geen bruikbare muisdata gevonden in deze lokale map. Controleer of data\\profiles\\master_profile.json of data\\recordings\\...\\points.csv aanwezig is."
        )

    runs = max(10, min(1000, int(runs)))
    rng = random.Random()
    baseline = {
        "duration_ms": [float(t.get("duration_s", 0.45)) * 1000 for t in templates],
        "curve_ratio": [float(t.get("curve_ratio", 1.12)) for t in templates],
        "overshoot_ratio": [float(t.get("overshoot_ratio", 0.0)) for t in templates],
        "corrections": [float(t.get("corrections", 0)) for t in templates],
        "click_delay_ms": [float(t.get("click_delay_s", 0.07)) * 1000 for t in templates],
    }

    generated: list[dict] = []
    cursor = (560.0, 350.0)
    corners = [(70.0, 70.0), (1050.0, 70.0), (70.0, 630.0), (1050.0, 630.0)]
    for index in range(runs):
        radius = rng.choice((rng.uniform(10, 18), rng.uniform(24, 38), rng.uniform(48, 70)))
        target = corners[index % 4] if index % 3 == 0 else (
            rng.uniform(radius + 35, 1120 - radius - 35),
            rng.uniform(radius + 35, 700 - radius - 35),
        )
        distance = math.dist(cursor, target)
        pool = sorted(templates, key=lambda t: abs(float(t.get("direct_distance", distance)) - distance))
        template = rng.choice(pool[: max(2, min(len(pool), max(5, len(pool) // 3)))])
        path, click_delay = generate_target_path(template, cursor, target, rng, radius)
        metrics = _measure(path, target, radius, click_delay)
        generated.append(metrics)
        cursor = (path[-1][1], path[-1][2])

    duration_scores = [_score(m["duration_ms"], baseline["duration_ms"]) for m in generated]
    curve_scores = [_score(m["curve_ratio"], baseline["curve_ratio"]) for m in generated]
    overshoot_scores = [_score(m["overshoot_ratio"], baseline["overshoot_ratio"]) for m in generated]
    correction_scores = [_score(m["corrections"], baseline["corrections"]) for m in generated]
    click_scores = [_score(m["click_delay_ms"], baseline["click_delay_ms"]) for m in generated]

    variability = min(100.0, 50.0 + 25.0 * min(1.0, _std([m["duration_ms"] for m in generated]) / max(1.0, _mean([m["duration_ms"] for m in generated]) * 0.18)) + 25.0 * min(1.0, _std([m["curve_ratio"] for m in generated]) / max(0.01, _mean([m["curve_ratio"] for m in generated]) * 0.08)))
    profile_match = _mean(curve_scores + duration_scores)
    timing_match = _mean(duration_scores + click_scores)
    target_behaviour = _mean(overshoot_scores + correction_scores)
    overall = round(profile_match * 0.38 + timing_match * 0.24 + target_behaviour * 0.23 + variability * 0.15, 1)
    confidence = round(min(100.0, 15.0 + math.log2(max(2, len(templates))) * 9.0 + min(25.0, info["aim_lab_templates"] * 0.8)), 1)

    result = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "runs": runs,
        "scores": {
            "hesse_profile_score": overall,
            "human_profile_match": round(profile_match, 1),
            "timing_match": round(timing_match, 1),
            "natural_variation": round(variability, 1),
            "target_behaviour": round(target_behaviour, 1),
            "data_confidence": confidence,
        },
        "data": info,
        "interpretation": "Sterke profielmatch" if overall >= 80 else "Redelijke profielmatch" if overall >= 65 else "Gemengd profiel" if overall >= 45 else "Duidelijk afwijkend",
        "confidence_label": "goed" if confidence >= 75 else "voorlopig" if confidence >= 40 else "laag",
        "run_results": generated,
    }
    folder = REPORTS / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "report.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("AI Mouse – Human Score Lab")
        root.geometry("900x620")
        root.minsize(760, 540)
        root.configure(bg=BG)
        self._build()

    def _build(self):
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True, padx=22, pady=20)
        tk.Label(shell, text="Human Score Lab", bg=BG, fg=TEXT, font=("Segoe UI", 24, "bold")).pack(anchor="w")
        tk.Label(shell, text="Test jouw huidige profiel met 100 nieuwe simulaties.", bg=BG, fg=MUTED).pack(anchor="w", pady=(3, 16))
        controls = tk.Frame(shell, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        controls.pack(fill="x")
        row = tk.Frame(controls, bg=PANEL)
        row.pack(fill="x", padx=14, pady=12)
        tk.Label(row, text="Aantal runs", bg=PANEL, fg=MUTED).pack(side="left")
        self.runs = tk.IntVar(value=100)
        tk.Spinbox(row, from_=10, to=1000, textvariable=self.runs, width=7, bg="#151d36", fg=TEXT, buttonbackground="#151d36", relief="flat").pack(side="left", padx=8)
        self.start = tk.Button(row, text="Start profieltest", command=self.run, bg=PURPLE, fg=TEXT, relief="flat", cursor="hand2", font=("Segoe UI", 10, "bold"), padx=20, pady=8)
        self.start.pack(side="left", padx=8)
        self.status = tk.Label(row, text="Klaar", bg=PANEL, fg=MUTED)
        self.status.pack(side="right")
        body = tk.Frame(shell, bg=BG)
        body.pack(fill="both", expand=True, pady=(12, 0))
        left = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        right = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        right.pack(side="right", fill="both", expand=True, padx=(6, 0))
        tk.Label(left, text="Hesse Profile Score", bg=PANEL, fg=MUTED, font=("Segoe UI", 11, "bold")).pack(pady=(24, 8))
        self.score = tk.Label(left, text="—", bg=PANEL, fg=GREEN, font=("Segoe UI", 40, "bold"))
        self.score.pack()
        self.interpretation = tk.Label(left, text="Nog niet getest", bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold"))
        self.interpretation.pack()
        self.details = tk.Label(left, text="", bg=PANEL, fg=MUTED, justify="left", font=("Segoe UI", 10))
        self.details.pack(anchor="w", padx=24, pady=22)
        tk.Label(right, text="Gebruikte data", bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(22, 10))
        self.data = tk.Label(right, text="Nog niet ingelezen", bg=PANEL, fg=MUTED, justify="left", font=("Segoe UI", 10))
        self.data.pack(anchor="w", padx=20)

    def run(self):
        self.start.config(state="disabled")
        self.status.config(text="Runs uitvoeren…", fg=YELLOW)
        self.root.update_idletasks()
        try:
            result = run_simulation(self.runs.get())
        except Exception as exc:
            self.start.config(state="normal")
            self.status.config(text="Fout", fg=RED)
            messagebox.showerror("Human Score Lab", str(exc))
            return
        self.start.config(state="normal")
        self.status.config(text="Voltooid", fg=GREEN)
        scores = result["scores"]
        info = result["data"]
        self.score.config(text=f"{scores['hesse_profile_score']:.0f} / 100")
        self.interpretation.config(text=result["interpretation"])
        self.details.config(text=(
            f"Profielmatch       {scores['human_profile_match']:.0f} / 100\n"
            f"Timingmatch        {scores['timing_match']:.0f} / 100\n"
            f"Variatie           {scores['natural_variation']:.0f} / 100\n"
            f"Targetgedrag       {scores['target_behaviour']:.0f} / 100\n\n"
            f"Datavertrouwen     {scores['data_confidence']:.0f} / 100 ({result['confidence_label']})"
        ))
        self.data.config(text=(
            f"Bruikbare templates: {info['usable_templates']}\n"
            f"Uit masterprofiel: {info['profile_templates']}\n"
            f"Legacy geconverteerd: {info['legacy_templates']}\n"
            f"Fallback recordings: {info['recording_fallback_templates']}\n"
            f"Aim Lab-templates: {info['aim_lab_templates']}"
        ))


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
