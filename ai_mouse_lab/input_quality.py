from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class RawInputQuality:
    received: int = 0
    valid: int = 0
    rejected: int = 0
    sequence_gaps: int = 0
    max_gap_ms: float = 0.0
    last_clock: float | None = None
    device_changes: int = 0
    active_device: str | None = None

    def inspect(self, clock: float, dx: int, dy: int, device_id: str = "unknown") -> tuple[bool, dict]:
        self.received += 1
        gap_ms = 0.0
        if self.last_clock is not None:
            gap_ms = max(0.0, (clock - self.last_clock) * 1000.0)
            self.max_gap_ms = max(self.max_gap_ms, gap_ms)
            if gap_ms > 100.0:
                self.sequence_gaps += 1
        self.last_clock = clock

        if self.active_device is None:
            self.active_device = device_id
        elif device_id != self.active_device:
            self.device_changes += 1

        magnitude = abs(dx) + abs(dy)
        valid = magnitude > 0 and magnitude < 200_000
        if valid:
            self.valid += 1
        else:
            self.rejected += 1

        return valid, {
            "sequence": self.received,
            "gap_ms": round(gap_ms, 4),
            "device_id": device_id,
            "quality": "valid" if valid else "rejected",
        }

    def inclusion_decision(self, raw_supported: bool) -> dict:
        reasons: list[str] = []
        if not raw_supported:
            reasons.append("raw_input_unsupported")
        if self.valid < 100:
            reasons.append("insufficient_raw_samples")
        if self.received and self.rejected / self.received > 0.01:
            reasons.append("too_many_rejected_samples")
        if self.sequence_gaps > max(3, self.valid // 500):
            reasons.append("raw_input_gaps")
        if self.device_changes:
            reasons.append("mixed_input_devices")
        return {
            "included_in_gaming_profile": not reasons,
            "diagnostic_only": bool(reasons),
            "reasons": reasons,
            "metrics": asdict(self),
        }
