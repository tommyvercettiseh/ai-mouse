from __future__ import annotations

import math
import random
from collections import Counter

from .models import TargetSpec


class BalancedTargetScheduler:
    """Balance size × distance at 25% each without exposing settings to the user."""

    COMBINATIONS = (
        ("small", "near"),
        ("small", "far"),
        ("large", "near"),
        ("large", "far"),
    )
    SHAPES = ("circle", "square", "triangle")
    REGIONS = ("center", "edge", "corner", "diagonal")

    def __init__(self, seed: int | None = None) -> None:
        self.random = random.Random(seed)
        self.combo_counts: Counter[tuple[str, str]] = Counter()
        self.shape_counts: Counter[str] = Counter()
        self.region_counts: Counter[str] = Counter()
        self.target_id = 0

    def _least_used(self, values, counts):
        minimum = min(counts[value] for value in values)
        choices = [value for value in values if counts[value] == minimum]
        return self.random.choice(choices)

    def next_target(
        self,
        previous: tuple[float, float] | None,
        width: int,
        height: int,
        shown_at: float,
    ) -> TargetSpec:
        width = max(320, int(width))
        height = max(240, int(height))
        previous = previous or (width / 2.0, height / 2.0)

        combo = self._least_used(self.COMBINATIONS, self.combo_counts)
        shape = self._least_used(self.SHAPES, self.shape_counts)
        region = self._least_used(self.REGIONS, self.region_counts)
        size_bucket, distance_bucket = combo

        min_side = min(width, height)
        radius = (
            self.random.uniform(min_side * 0.018, min_side * 0.028)
            if size_bucket == "small"
            else self.random.uniform(min_side * 0.047, min_side * 0.068)
        )
        radius = max(10.0, radius)
        center = self._place(previous, width, height, radius, distance_bucket, region)

        self.combo_counts[combo] += 1
        self.shape_counts[shape] += 1
        self.region_counts[region] += 1
        self.target_id += 1
        return TargetSpec(
            target_id=self.target_id,
            shape=shape,
            size_bucket=size_bucket,
            distance_bucket=distance_bucket,
            region_bucket=region,
            center_x=round(center[0], 3),
            center_y=round(center[1], 3),
            radius=round(radius, 3),
            shown_at=float(shown_at),
        )

    def _place(
        self,
        previous: tuple[float, float],
        width: int,
        height: int,
        radius: float,
        distance_bucket: str,
        region: str,
    ) -> tuple[float, float]:
        diagonal = math.hypot(width, height)
        if distance_bucket == "near":
            min_distance, max_distance = diagonal * 0.10, diagonal * 0.30
        else:
            min_distance, max_distance = diagonal * 0.45, diagonal * 0.76

        margin = radius + 18.0
        best = (width / 2.0, height / 2.0)
        best_error = float("inf")
        for _ in range(180):
            candidate = self._candidate(region, width, height, margin)
            distance = math.hypot(candidate[0] - previous[0], candidate[1] - previous[1])
            if min_distance <= distance <= max_distance:
                return candidate
            error = min(abs(distance - min_distance), abs(distance - max_distance))
            if error < best_error:
                best, best_error = candidate, error
        return best

    def _candidate(
        self, region: str, width: int, height: int, margin: float
    ) -> tuple[float, float]:
        r = self.random
        if region == "center":
            return r.uniform(width * 0.25, width * 0.75), r.uniform(
                height * 0.25, height * 0.75
            )
        if region == "edge":
            side = r.choice(("left", "right", "top", "bottom"))
            if side == "left":
                return r.uniform(margin, width * 0.16), r.uniform(margin, height - margin)
            if side == "right":
                return r.uniform(width * 0.84, width - margin), r.uniform(
                    margin, height - margin
                )
            if side == "top":
                return r.uniform(margin, width - margin), r.uniform(margin, height * 0.16)
            return r.uniform(margin, width - margin), r.uniform(height * 0.84, height - margin)
        if region == "corner":
            left = r.choice((True, False))
            top = r.choice((True, False))
            x = r.uniform(margin, width * 0.24) if left else r.uniform(width * 0.76, width - margin)
            y = r.uniform(margin, height * 0.24) if top else r.uniform(height * 0.76, height - margin)
            return x, y
        # Diagonal zone: both axes change meaningfully.
        if r.random() < 0.5:
            return r.uniform(width * 0.14, width * 0.36), r.uniform(height * 0.64, height * 0.86)
        return r.uniform(width * 0.64, width * 0.86), r.uniform(height * 0.14, height * 0.36)
