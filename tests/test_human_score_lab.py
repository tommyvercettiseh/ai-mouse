from ai_mouse_hub.human_score_lab import baseline_from_templates, measure_run


def test_measure_run_tracks_curve_and_click_timing():
    path = [
        (0.0, 0.0, 0.0),
        (0.1, 45.0, 5.0),
        (0.2, 105.0, 0.0),
        (0.3, 100.0, 0.0),
    ]
    result = measure_run(path, (100.0, 0.0), 10.0, 0.075)
    assert result.duration_ms == 300.0
    assert result.travelled_distance > result.direct_distance
    assert result.click_delay_ms == 75.0
    assert result.curve_ratio > 1.0


def test_baseline_uses_profile_template_fields():
    baseline = baseline_from_templates([
        {
            "duration_s": 0.5,
            "curve_ratio": 1.2,
            "overshoot_ratio": 0.04,
            "corrections": 2,
            "click_delay_s": 0.08,
            "direct_distance": 320,
        }
    ])
    assert baseline["duration_ms"] == [500.0]
    assert baseline["click_delay_ms"] == [80.0]
    assert baseline["corrections"] == [2.0]
