from ai_mouse_lab.aim_metrics import analyze_attempt, inside_target
from ai_mouse_lab.models import TargetSpec


def target(shape: str = "circle") -> TargetSpec:
    return TargetSpec(1, shape, "small", "near", "center", 100.0, 100.0, 20.0, 0.0)


def test_target_shapes():
    assert inside_target(100, 100, target("circle"))
    assert not inside_target(130, 100, target("circle"))
    assert inside_target(115, 115, target("square"))
    assert inside_target(100, 100, target("triangle"))


def test_attempt_logs_overshoot_timing_and_hold():
    path = [(0.0, 0.0, 100.0), (0.1, 70.0, 100.0), (0.2, 125.0, 100.0), (0.3, 100.0, 100.0)]
    result = analyze_attempt(path, target(), 0.35, 0.43, (100.0, 100.0))
    assert result["click_hit"]
    assert result["click_hold_ms"] == 80.0
    assert result["mean_speed_px_s"] > 0
    assert result["overshoot_px"] >= 0
