from ai_mouse_hub.aim_lab_v2 import _inside_target, path_metrics


def test_inside_circle_square_and_triangle():
    target = (100.0, 100.0)
    assert _inside_target(100, 100, target, 20, "circle")
    assert not _inside_target(130, 100, target, 20, "circle")
    assert _inside_target(115, 115, target, 20, "square")
    assert not _inside_target(125, 125, target, 20, "square")
    assert _inside_target(100, 100, target, 20, "triangle")
    assert not _inside_target(100, 125, target, 20, "triangle")


def test_path_metrics_include_timing_speed_and_accuracy():
    path = [
        (0.0, 0.0, 0.0),
        (0.1, 60.0, 0.0),
        (0.2, 105.0, 0.0),
        (0.3, 100.0, 0.0),
    ]
    result = path_metrics(path, (100.0, 0.0), 10.0, 0.05, 0.12, 0.08)
    assert result.travelled_distance > result.direct_distance
    assert result.movement_ms == 300.0
    assert result.click_delay_ms == 50.0
    assert result.click_hold_ms == 80.0
    assert result.mean_speed_px_s > 0
    assert result.peak_speed_px_s >= result.mean_speed_px_s
    assert result.accuracy_percent == 100.0
