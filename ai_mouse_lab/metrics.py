from __future__ import annotations

import math
from collections.abc import Sequence

from .models import MovementMetrics

Point = tuple[float, float, float]  # elapsed seconds, x, y


def euclidean(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def path_length(points: Sequence[Point]) -> float:
    return sum(
        euclidean((left[1], left[2]), (right[1], right[2]))
        for left, right in zip(points, points[1:])
    )


def peak_speed(points: Sequence[Point]) -> float:
    peak = 0.0
    for left, right in zip(points, points[1:]):
        dt = right[0] - left[0]
        if dt <= 0:
            continue
        peak = max(peak, euclidean((left[1], left[2]), (right[1], right[2])) / dt)
    return peak


def correction_count(points: Sequence[Point], threshold_degrees: float = 30.0) -> int:
    """Count meaningful heading changes while ignoring tiny jitter segments."""
    vectors: list[tuple[float, float]] = []
    for left, right in zip(points, points[1:]):
        dx = right[1] - left[1]
        dy = right[2] - left[2]
        if math.hypot(dx, dy) >= 2.0:
            vectors.append((dx, dy))

    count = 0
    for first, second in zip(vectors, vectors[1:]):
        dot = first[0] * second[0] + first[1] * second[1]
        denom = math.hypot(*first) * math.hypot(*second)
        if denom <= 0:
            continue
        angle = math.degrees(math.acos(max(-1.0, min(1.0, dot / denom))))
        if angle >= threshold_degrees:
            count += 1
    return count


def classify_distance(
    direct_distance_px: float,
    monitor_diagonal_px: float,
    monitor_transition: bool = False,
) -> str:
    if monitor_transition:
        return "screen_transition"
    ratio = direct_distance_px / max(1.0, monitor_diagonal_px)
    if ratio < 0.03:
        return "micro"
    if ratio < 0.12:
        return "short"
    if ratio < 0.30:
        return "medium"
    return "long"


def analyze_movement(
    points: Sequence[Point],
    monitor_diagonal_px: float,
    monitor_transition: bool = False,
) -> MovementMetrics | None:
    if len(points) < 2:
        return None
    direct = euclidean((points[0][1], points[0][2]), (points[-1][1], points[-1][2]))
    travelled = path_length(points)
    duration = max(0.0, points[-1][0] - points[0][0])
    if duration <= 0 or travelled < 1.0:
        return None
    mean_speed = travelled / duration
    efficiency = direct / travelled if travelled else 0.0
    return MovementMetrics(
        direct_distance_px=round(direct, 3),
        travelled_distance_px=round(travelled, 3),
        duration_ms=round(duration * 1000.0, 3),
        mean_speed_px_s=round(mean_speed, 3),
        peak_speed_px_s=round(peak_speed(points), 3),
        efficiency=round(max(0.0, min(1.0, efficiency)), 5),
        correction_count=correction_count(points),
        distance_bucket=classify_distance(direct, monitor_diagonal_px, monitor_transition),
        monitor_transition=bool(monitor_transition),
    )


def normalize_trace(points: Sequence[Point]) -> list[list[float]]:
    if len(points) < 2:
        return []
    t0, x0, y0 = points[0]
    direct = euclidean((x0, y0), (points[-1][1], points[-1][2]))
    scale = max(1.0, direct)
    duration = max(0.001, points[-1][0] - t0)
    return [
        [
            round((t - t0) / duration, 6),
            round((x - x0) / scale, 6),
            round((y - y0) / scale, 6),
        ]
        for t, x, y in points
    ]
