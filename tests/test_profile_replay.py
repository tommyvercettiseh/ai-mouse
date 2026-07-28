from ai_mouse_lab.profile_replay import generate_profile_trace


def test_zero_percent_profile_is_nearly_straight():
    points = generate_profile_trace(
        (0.0, 0.0),
        (1000.0, 0.0),
        {"profile_progress_percent": 0, "templates": []},
        points=50,
    )
    assert points[0][0] == 0.0
    assert points[-1] == (1000.0, 0.0)
    assert max(abs(y) for _, y in points) < 0.001


def test_learned_profile_adds_curve_but_keeps_destination():
    template = [
        [index / 9.0, index / 9.0, 0.3 * (index / 9.0)]
        for index in range(10)
    ]
    profile = {
        "profile_progress_percent": 80,
        "templates": [{"points": template}],
        "source_counts": {"aim_lab_targets": 100},
    }
    points = generate_profile_trace((0.0, 0.0), (1000.0, 0.0), profile, points=50)
    assert points[-1] == (1000.0, 0.0)
    assert max(abs(y) for _, y in points) > 1.0
