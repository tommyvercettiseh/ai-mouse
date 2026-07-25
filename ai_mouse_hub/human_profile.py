from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class HumanTemplate:
    points: list[tuple[float, float, float]]
    duration_s: float
    click_delay_s: float
    direct_distance: float
    travelled_distance: float
    curve_ratio: float
    overshoot_ratio: float
    corrections: int
    context: str
    quality: float

    def to_dict(self) -> dict:
        return {
            "points": [[round(t, 6), round(u, 6), round(v, 6)] for t, u, v in self.points],
            "duration_s": round(self.duration_s, 6),
            "click_delay_s": round(self.click_delay_s, 6),
            "direct_distance": round(self.direct_distance, 3),
            "travelled_distance": round(self.travelled_distance, 3),
            "curve_ratio": round(self.curve_ratio, 5),
            "overshoot_ratio": round(self.overshoot_ratio, 5),
            "corrections": self.corrections,
            "context": self.context,
            "quality": round(self.quality, 3),
        }


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _normalise_segment(points: Sequence[tuple[float, float, float]]) -> HumanTemplate | None:
    if len(points) < 8:
        return None
    start = (points[0][1], points[0][2])
    end = (points[-1][1], points[-1][2])
    dx, dy = end[0] - start[0], end[1] - start[1]
    direct = math.hypot(dx, dy)
    duration = points[-1][0] - points[0][0]
    if direct < 12 or duration <= 0.03:
        return None
    ux, uy = dx / direct, dy / direct
    px, py = -uy, ux
    travelled = 0.0
    local: list[tuple[float, float, float]] = []
    previous = start
    along_values: list[float] = []
    distances_to_end: list[float] = []
    for timestamp, x, y in points:
        current = (x, y)
        travelled += _distance(previous, current)
        previous = current
        rel_x, rel_y = x - start[0], y - start[1]
        along = (rel_x * ux + rel_y * uy) / direct
        perpendicular = (rel_x * px + rel_y * py) / direct
        local.append(((timestamp - points[0][0]) / duration, along, perpendicular))
        along_values.append(along)
        distances_to_end.append(_distance(current, end) / direct)
    overshoot = max(0.0, max(along_values) - 1.0)
    corrections = 0
    for a, b, c in zip(distances_to_end, distances_to_end[1:], distances_to_end[2:]):
        if b < a and c > b + 0.002:
            corrections += 1
    curve = travelled / direct
    quality = 1.0
    if curve > 2.8:
        quality -= 0.35
    if duration > 2.5:
        quality -= 0.2
    if max(abs(v) for _, _, v in local) > 1.2:
        quality -= 0.25
    return HumanTemplate(local, duration, 0.0, direct, travelled, curve, overshoot, corrections, "Unknown", max(0.0, quality))


def extract_click_templates(path: Path, context: str, max_lookback_s: float = 1.6) -> list[HumanTemplate]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    parsed: list[dict] = []
    for row in rows:
        try:
            parsed.append({
                "timestamp": float(row["timestamp"]),
                "x": float(row["x"]),
                "y": float(row["y"]),
                "event_type": row.get("event_type", "move"),
                "button": row.get("button", ""),
                "pressed": row.get("pressed", ""),
            })
        except (KeyError, TypeError, ValueError):
            continue
    templates: list[HumanTemplate] = []
    for index, row in enumerate(parsed):
        if row["event_type"] != "click" or row["pressed"] not in {"1", "True", "true"}:
            continue
        click_time = row["timestamp"]
        segment: list[tuple[float, float, float]] = []
        previous_time = click_time
        for candidate in reversed(parsed[:index]):
            if candidate["event_type"] != "move":
                continue
            if click_time - candidate["timestamp"] > max_lookback_s:
                break
            if segment and previous_time - candidate["timestamp"] > 0.28:
                break
            segment.append((candidate["timestamp"], candidate["x"], candidate["y"]))
            previous_time = candidate["timestamp"]
        segment.reverse()
        if not segment:
            continue
        segment.append((click_time, row["x"], row["y"]))
        template = _normalise_segment(segment)
        if template is None or template.quality < 0.45:
            continue
        last_move_time = segment[-2][0] if len(segment) > 1 else click_time
        templates.append(HumanTemplate(
            template.points,
            template.duration_s,
            max(0.0, click_time - last_move_time),
            template.direct_distance,
            template.travelled_distance,
            template.curve_ratio,
            template.overshoot_ratio,
            template.corrections,
            context,
            template.quality,
        ))
    return templates


def generate_target_path(
    template: dict,
    start: tuple[float, float],
    target: tuple[float, float],
    rng: random.Random,
    target_radius: float,
) -> tuple[list[tuple[float, float, float]], float]:
    points = template.get("points") or []
    if len(points) < 2:
        return [(0.0, *start), (0.4, *target)], 0.06
    dx, dy = target[0] - start[0], target[1] - start[1]
    distance = max(1.0, math.hypot(dx, dy))
    ux, uy = dx / distance, dy / distance
    px, py = -uy, ux
    duration = max(0.12, float(template.get("duration_s", 0.45)) * (distance / max(40.0, float(template.get("direct_distance", distance)))) ** 0.28)
    variation = rng.gauss(1.0, 0.045)
    curve_scale = rng.gauss(1.0, 0.08)
    out: list[tuple[float, float, float]] = []
    for raw in points:
        t, along, perpendicular = map(float, raw[:3])
        local_along = along * distance
        local_perp = perpendicular * distance * curve_scale
        x = start[0] + local_along * ux + local_perp * px
        y = start[1] + local_along * uy + local_perp * py
        out.append((max(0.0, min(1.0, t)) * duration * variation, x, y))
    final_offset = min(target_radius * 0.28, max(1.0, rng.gauss(target_radius * 0.08, target_radius * 0.05)))
    angle = rng.uniform(0, math.tau)
    out[-1] = (out[-1][0], target[0] + math.cos(angle) * final_offset, target[1] + math.sin(angle) * final_offset)
    click_delay = max(0.02, min(0.22, rng.gauss(float(template.get("click_delay_s", 0.07)) or 0.07, 0.018)))
    return out, click_delay


def select_template(templates: Sequence[dict], distance: float, context: str, rng: random.Random) -> dict | None:
    if not templates:
        return None
    matching = [item for item in templates if str(item.get("context", "")).lower() == context.lower()]
    pool = matching or list(templates)
    pool = sorted(pool, key=lambda item: abs(float(item.get("direct_distance", distance)) - distance))[: max(5, len(pool) // 3)]
    weights = [max(0.1, float(item.get("quality", 0.5))) for item in pool]
    return rng.choices(pool, weights=weights, k=1)[0]
