from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .paths import CALIBRATION_FILE, ensure_data_dirs


@dataclass
class GamingCalibration:
    counts_per_360_x: float | None = None
    counts_per_180_y: float | None = None


def load_calibration(profile: str = "default") -> GamingCalibration:
    ensure_data_dirs()
    if not CALIBRATION_FILE.exists():
        return GamingCalibration()
    try:
        data = json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))
        row = data.get(profile) or data.get("default") or {}
        return GamingCalibration(
            counts_per_360_x=_positive_or_none(row.get("counts_per_360_x")),
            counts_per_180_y=_positive_or_none(row.get("counts_per_180_y")),
        )
    except Exception:
        return GamingCalibration()


def save_calibration(calibration: GamingCalibration, profile: str = "default") -> None:
    ensure_data_dirs()
    data: dict[str, Any] = {}
    if CALIBRATION_FILE.exists():
        try:
            parsed = json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                data = parsed
        except Exception:
            data = {}
    data[profile] = {
        "counts_per_360_x": calibration.counts_per_360_x,
        "counts_per_180_y": calibration.counts_per_180_y,
    }
    CALIBRATION_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _positive_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


class RelativeViewTracker:
    """Unwrap relative mouse counts into an unlimited virtual view."""

    def __init__(self, calibration: GamingCalibration | None = None) -> None:
        self.calibration = calibration or GamingCalibration()
        self.raw_x = 0.0
        self.raw_y = 0.0
        self.yaw_deg = 0.0
        self.pitch_deg = 0.0

    def add(self, dx: float, dy: float) -> dict[str, float | None]:
        self.raw_x += dx
        self.raw_y += dy
        if self.calibration.counts_per_360_x:
            self.yaw_deg += dx / self.calibration.counts_per_360_x * 360.0
        if self.calibration.counts_per_180_y:
            self.pitch_deg += dy / self.calibration.counts_per_180_y * 180.0
        return {
            "virtual_raw_x": round(self.raw_x, 3),
            "virtual_raw_y": round(self.raw_y, 3),
            "yaw_deg": round(self.yaw_deg, 4)
            if self.calibration.counts_per_360_x
            else None,
            "pitch_deg": round(self.pitch_deg, 4)
            if self.calibration.counts_per_180_y
            else None,
        }
