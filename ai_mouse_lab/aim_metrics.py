from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from .metrics import correction_count, euclidean, path_length, peak_speed
from .models import TargetSpec

Point = tuple[float, float, float]


def inside_target(x: float, y: float, target: TargetSpec) -> bool:
    cx, cy = target.center
    radius = target.radius
    if target.shape == "circle":
        return math.hypot(x - cx, y - cy) <= radius
    if target.shape == "square":
        return abs(x - cx) <= radius and abs(y - cy) <= radius
    # Upward equilateral-style triangle, tested with barycentric signs.
    p1 = (cx, cy - radius)
    p2 = (cx - radius, cy + radius)
    p3 = (cx + radius, cy + radius)

    def sign(p, a, b):
        return (p[0] - b[0]) * (a[1] - b[1]) - (a[0] - b[0]) * (p[1] - b[1])

    point = (x, y)
    d1, d2, d3 = sign(point, p1, p2), sign(point, p2, p3), sign(point, p3, p1)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


def analyze_attempt(
    path: Sequence[Point],
    target: TargetSpec,
    click_down_t: float,
    click_up_t: float,
    click_xy: tuple[float, float],
    miss_count: int = 0,
) -> dict[str, Any]:
    if not path:
        path = [(0.0, click_xy[0], click_xy[1])]
    start = path[0]
    start_xy = (start[1], start[2])
    direct = euclidean(start_xy, target.center)
    travelled = path_length(path)
    duration = max(0.0, path[-1][0] - path[0][0])

    movement_start_t = path[0][0]
    for t, x, y in path[1:]:
        if euclidean(start_xy, (x, y)) >= 3.0:
            movement_start_t = t
            break

    first_entry_t: float | None = None
    exited_after_entry = False
    was_inside = False
    for t, x, y in path:
        now_inside = inside_target(x, y, target)
        if now_inside and first_entry_t is None:
            first_entry_t = t
        if first_entry_t is not None and was_inside and not now_inside:
            exited_after_entry = True
        was_inside = now_inside

    ux = (target.center_x - start[1]) / max(1.0, direct)
    uy = (target.center_y - start[2]) / max(1.0, direct)
    projections = [
        (x - start[1]) * ux + (y - start[2]) * uy for _, x, y in path
    ]
    overshoot_px = max(0.0, max(projections, default=0.0) - direct - target.radius)
    end_offset = euclidean(click_xy, target.center)
    click_hit = inside_target(click_xy[0], click_xy[1], target)
    reaction_ms = max(0.0, movement_start_t - target.shown_at) * 1000.0
    arrival_t = first_entry_t if first_entry_t is not None else click_down_t
    movement_ms = max(0.0, arrival_t - movement_start_t) * 1000.0
    click_delay_ms = max(0.0, click_down_t - arrival_t) * 1000.0
    hold_ms = max(0.0, click_up_t - click_down_t) * 1000.0

    return {
        **target.to_dict(),
        "click_hit": click_hit,
        "miss_count": int(miss_count),
        "reaction_ms": round(reaction_ms, 3),
        "movement_ms": round(movement_ms, 3),
        "click_delay_ms": round(click_delay_ms, 3),
        "click_hold_ms": round(hold_ms, 3),
        "direct_distance_px": round(direct, 3),
        "travelled_distance_px": round(travelled, 3),
        "path_efficiency": round(direct / travelled, 5) if travelled else 0.0,
        "mean_speed_px_s": round(travelled / duration, 3) if duration > 0 else 0.0,
        "peak_speed_px_s": round(peak_speed(path), 3),
        "overshoot_px": round(overshoot_px, 3),
        "exited_after_entry": bool(exited_after_entry),
        "correction_count": correction_count(path),
        "end_offset_px": round(end_offset, 3),
        "click_x": round(click_xy[0], 3),
        "click_y": round(click_xy[1], 3),
        "path": [[round(t, 6), round(x, 3), round(y, 3)] for t, x, y in path],
    }
