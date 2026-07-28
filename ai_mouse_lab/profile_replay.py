from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

from .paths import MASTER_PROFILE_FILE


def load_profile(path: Path = MASTER_PROFILE_FILE) -> dict[str, Any]:
    if not path.exists():
        return {"profile_progress_percent": 0, "templates": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"profile_progress_percent": 0, "templates": []}


def _sample_template(profile: dict[str, Any]) -> list[list[float]]:
    candidates = [
        row.get("points")
        for row in profile.get("templates", [])
        if isinstance(row.get("points"), list) and len(row.get("points")) >= 3
    ]
    return random.choice(candidates) if candidates else []


def generate_profile_trace(
    start: tuple[float, float],
    end: tuple[float, float],
    profile: dict[str, Any] | None = None,
    *,
    points: int = 90,
) -> list[tuple[float, float]]:
    """Generate a confidence-weighted visual replay from learned mouse data.

    At 0% confidence the path is straight. Curve, micro-variation and proven
    Aim Lab overshoot are introduced only as the data confidence grows.
    """

    profile = profile or load_profile()
    confidence = max(0.0, min(1.0, float(profile.get("profile_progress_percent", 0)) / 100.0))
    sx, sy = start
    ex, ey = end
    dx, dy = ex - sx, ey - sy
    length = max(1.0, math.hypot(dx, dy))
    nx, ny = -dy / length, dx / length
    template = _sample_template(profile)

    output: list[tuple[float, float]] = []
    for index in range(max(3, points)):
        t = index / (max(3, points) - 1)
        base_x = sx + dx * t
        base_y = sy + dy * t
        curve = 0.0
        if template:
            source_index = min(len(template) - 1, round(t * (len(template) - 1)))
            source = template[source_index]
            if isinstance(source, list) and len(source) >= 3:
                # normalize_trace stores [relative_time, forward_x, lateral_y].
                curve = float(source[2]) * length * 0.16
        else:
            curve = math.sin(t * math.pi) * length * 0.02

        overshoot = 0.0
        aim_count = int(profile.get("source_counts", {}).get("aim_lab_targets", 0) or 0)
        if aim_count >= 40 and t > 0.88:
            overshoot = math.sin((t - 0.88) / 0.12 * math.pi) * length * 0.025

        jitter = random.uniform(-1.0, 1.0) * confidence * 0.55
        output.append(
            (
                base_x + nx * (curve * confidence + jitter) + dx / length * overshoot * confidence,
                base_y + ny * (curve * confidence + jitter) + dy / length * overshoot * confidence,
            )
        )
    output[-1] = end
    return output
