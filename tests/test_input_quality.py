from ai_mouse_lab.input_quality import RawInputQuality


def test_clean_raw_stream_is_included_after_enough_samples():
    quality = RawInputQuality()
    for index in range(120):
        valid, payload = quality.inspect(index * 0.001, 2, -1)
        assert valid
        assert payload["sequence"] == index + 1
    decision = quality.inclusion_decision(raw_supported=True)
    assert decision["included_in_gaming_profile"] is True
    assert decision["reasons"] == []


def test_short_stream_is_diagnostic_only():
    quality = RawInputQuality()
    for index in range(20):
        quality.inspect(index * 0.001, 1, 1)
    decision = quality.inclusion_decision(raw_supported=True)
    assert decision["included_in_gaming_profile"] is False
    assert "insufficient_raw_samples" in decision["reasons"]


def test_large_invalid_delta_is_rejected():
    quality = RawInputQuality()
    valid, payload = quality.inspect(1.0, 500_000, 0)
    assert valid is False
    assert payload["quality"] == "rejected"


def test_device_change_blocks_profile_inclusion():
    quality = RawInputQuality()
    for index in range(120):
        device = "mouse-a" if index < 60 else "mouse-b"
        quality.inspect(index * 0.001, 2, 1, device)
    decision = quality.inclusion_decision(raw_supported=True)
    assert "mixed_input_devices" in decision["reasons"]
