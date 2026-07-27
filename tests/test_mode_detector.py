from ai_mouse_lab.mode_detector import InputModeDetector


def test_normal_absolute_motion_is_not_marked_as_gaming():
    detector = InputModeDetector()
    detector.add_absolute(0.0, 10, 10)
    detector.add_raw(0.05, 20, 0)
    detector.add_absolute(0.05, 30, 10)
    assert detector.mode == "absolute"


def test_large_raw_motion_with_stationary_cursor_is_gaming():
    detector = InputModeDetector()
    detector.add_absolute(0.0, 500, 500)
    for index in range(20):
        detector.add_raw(0.01 * index, 25, 0)
        detector.add_absolute(0.01 * index, 500, 500)
    assert detector.mode == "gaming"
