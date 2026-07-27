from ai_mouse_lab.gaming import GamingCalibration, RelativeViewTracker


def test_relative_view_is_unbounded_and_can_convert_to_degrees():
    tracker = RelativeViewTracker(GamingCalibration(counts_per_360_x=1000, counts_per_180_y=500))
    result = tracker.add(2500, 1000)
    assert result["virtual_raw_x"] == 2500
    assert result["yaw_deg"] == 900.0
    assert result["pitch_deg"] == 360.0
