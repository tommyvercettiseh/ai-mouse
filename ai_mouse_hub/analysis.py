from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class CleanPoint:
    timestamp: float
    x: float
    y: float
    segment_id: int


@dataclass(frozen=True)
class AnalysisSummary:
    raw_points: int
    clean_points: int
    segment_count: int
    warp_count: int
    pause_count: int
    median_interval_ms: float


def _median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def clean_and_segment(
    points: Iterable[tuple[float, float, float]],
    *,
    pause_seconds: float = 0.35,
    warp_speed_px_s: float = 18000.0,
    warp_distance_px: float = 250.0,
) -> tuple[list[CleanPoint], AnalysisSummary]:
    """Split raw global points into safe movement segments.

    Long pauses start a new segment. Extremely fast, long jumps are treated as
    cursor warps and are never connected in replay or profile templates.
    Raw data is not modified.
    """
    source = [(float(t), float(x), float(y)) for t, x, y in points]
    if not source:
        return [], AnalysisSummary(0, 0, 0, 0, 0, 0.0)

    clean: list[CleanPoint] = []
    segment_id = 0
    warp_count = 0
    pause_count = 0
    intervals: list[float] = []
    previous: tuple[float, float, float] | None = None

    for t, x, y in source:
        if not all(math.isfinite(value) for value in (t, x, y)):
            continue
        if previous is not None:
            pt, px, py = previous
            dt = t - pt
            if dt <= 0:
                segment_id += 1
                previous = (t, x, y)
                clean.append(CleanPoint(t, x, y, segment_id))
                continue
            intervals.append(dt)
            distance = math.hypot(x - px, y - py)
            speed = distance / dt
            if dt >= pause_seconds:
                pause_count += 1
                segment_id += 1
            elif distance >= warp_distance_px and speed >= warp_speed_px_s:
                warp_count += 1
                segment_id += 1
        clean.append(CleanPoint(t, x, y, segment_id))
        previous = (t, x, y)

    segment_count = len({point.segment_id for point in clean}) if clean else 0
    summary = AnalysisSummary(
        raw_points=len(source),
        clean_points=len(clean),
        segment_count=segment_count,
        warp_count=warp_count,
        pause_count=pause_count,
        median_interval_ms=round(_median(intervals) * 1000.0, 2),
    )
    return clean, summary


def segments(points: Sequence[CleanPoint]) -> list[list[CleanPoint]]:
    grouped: list[list[CleanPoint]] = []
    current_id: int | None = None
    for point in points:
        if current_id != point.segment_id:
            grouped.append([])
            current_id = point.segment_id
        grouped[-1].append(point)
    return [group for group in grouped if len(group) >= 2]
