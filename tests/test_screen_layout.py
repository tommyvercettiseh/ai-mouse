from ai_mouse_hub.screen_layout import MonitorInfo, monitor_for_point


def test_monitor_for_point_supports_negative_coordinates():
    monitors = [
        MonitorInfo(1, -1920, 0, 1920, 1080, False),
        MonitorInfo(2, 0, 0, 2560, 1440, True),
    ]
    assert monitor_for_point(monitors, -100, 500).index == 1
    assert monitor_for_point(monitors, 100, 500).index == 2


def test_monitor_edges_do_not_overlap():
    monitors = [
        MonitorInfo(1, 0, 0, 1920, 1080, True),
        MonitorInfo(2, 1920, 0, 1920, 1080, False),
    ]
    assert monitor_for_point(monitors, 1919, 100).index == 1
    assert monitor_for_point(monitors, 1920, 100).index == 2
    assert monitor_for_point(monitors, 5000, 100) is None
