from ai_mouse_lab.metrics import analyze_movement, classify_distance


def test_distance_buckets_are_relative_to_monitor_size():
    diagonal = 1000.0
    assert classify_distance(10, diagonal) == "micro"
    assert classify_distance(80, diagonal) == "short"
    assert classify_distance(200, diagonal) == "medium"
    assert classify_distance(400, diagonal) == "long"
    assert classify_distance(10, diagonal, monitor_transition=True) == "screen_transition"


def test_movement_metrics_include_speed_efficiency_and_corrections():
    points = [(0.0, 0.0, 0.0), (0.1, 40.0, 0.0), (0.2, 80.0, 10.0), (0.3, 100.0, 0.0)]
    result = analyze_movement(points, monitor_diagonal_px=1000.0)
    assert result is not None
    assert result.travelled_distance_px >= result.direct_distance_px
    assert result.mean_speed_px_s > 0
    assert result.peak_speed_px_s >= result.mean_speed_px_s
    assert 0 < result.efficiency <= 1
