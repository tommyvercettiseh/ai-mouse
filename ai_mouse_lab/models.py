from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class MonitorInfo:
    index: int
    x: int
    y: int
    width: int
    height: int
    primary: bool = False

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def diagonal(self) -> float:
        return (self.width**2 + self.height**2) ** 0.5

    def contains(self, x: float, y: float) -> bool:
        return self.x <= x < self.right and self.y <= y < self.bottom

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MovementMetrics:
    direct_distance_px: float
    travelled_distance_px: float
    duration_ms: float
    mean_speed_px_s: float
    peak_speed_px_s: float
    efficiency: float
    correction_count: int
    distance_bucket: str
    monitor_transition: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TargetSpec:
    target_id: int
    shape: str
    size_bucket: str
    distance_bucket: str
    region_bucket: str
    center_x: float
    center_y: float
    radius: float
    shown_at: float

    @property
    def center(self) -> tuple[float, float]:
        return self.center_x, self.center_y

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
