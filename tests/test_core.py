from __future__ import annotations

import json
import random
from pathlib import Path

import ai_mouse_hub.analysis as analysis
import ai_mouse_hub.core as core
import ai_mouse_hub.global_recorder as recorder
from ai_mouse_hub.click_test import path_metrics, transform_template


def test_normalize_and_replay():
    points = [(0.0, 0.0, 0.0), (0.1, 50.0, 25.0), (0.2, 100.0, 100.0)]
    normalized = core.normalize_path(points, count=16)
    assert len(normalized) == 16
    replay = core.generate_replay(normalized, random.Random(42))
    assert replay[0] == normalized[0]
    assert replay[-1] == normalized[-1]
    assert 0 < core.similarity(normalized, replay) <= 100


def _redirect_data(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(core, "DATA", tmp_path)
    monkeypatch.setattr(core, "RECORDINGS", tmp_path / "recordings")
    monkeypatch.setattr(core, "PROFILES", tmp_path / "profiles")
    monkeypatch.setattr(core, "REPORTS", tmp_path / "stress_lab")
    monkeypatch.setattr(core, "LOGS", tmp_path / "logs")
    monkeypatch.setattr(recorder, "RECORDINGS", core.RECORDINGS)
    for folder in (core.RECORDINGS, core.PROFILES, core.REPORTS, core.LOGS):
        folder.mkdir(parents=True, exist_ok=True)


def test_recording_profile_and_stress(tmp_path: Path, monkeypatch):
    _redirect_data(tmp_path, monkeypatch)
    points = [(i * 0.01, float(i * 3), float(i * 2 + (i % 5))) for i in range(150)]
    core.save_recording("Browsing", points)
    sessions = core.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].point_count == 150
    profile = core.build_master_profile(sessions)
    assert profile["source_count"] == 1
    first = core.run_stress_test(25, 42)
    second = core.run_stress_test(25, 42)
    assert 0 <= first["scores"]["overall"] <= 100
    assert first["scores"] == second["scores"]
    assert json.loads((Path(first["result_folder"]) / "report.json").read_text(encoding="utf-8"))["runs"] == 25


def test_global_recording_writes_mouse_only_privacy_metadata(tmp_path: Path, monkeypatch):
    _redirect_data(tmp_path, monkeypatch)
    monkeypatch.setattr(recorder, "virtual_screen_bounds", lambda: (-1920, 0, 3840, 1080))
    events = [
        recorder.MouseEvent(0.0, "move", -100.0, 200.0, window_title="Browser"),
        recorder.MouseEvent(0.1, "click", 20.0, 220.0, button="Button.left", pressed=True, window_title="Browser"),
        recorder.MouseEvent(0.2, "scroll", 30.0, 230.0, scroll_dy=-1.0, window_title="Game"),
    ]
    folder = recorder.save_global_recording("Gaming", events)
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    rows = (folder / "points.csv").read_text(encoding="utf-8").splitlines()
    assert metadata["recording_scope"] == "global_mouse_only"
    assert metadata["privacy"]["keyboard_recorded"] is False
    assert metadata["privacy"]["typed_text_recorded"] is False
    assert metadata["virtual_screen"]["left"] == -1920
    assert set(metadata["window_titles"]) == {"Browser", "Game"}
    assert "event_type" in rows[0]


def test_global_recorder_samples_moves_without_keyboard_hooks(monkeypatch):
    captured = []
    instance = recorder.GlobalMouseRecorder(on_event=captured.append, sample_interval=0.01)
    instance.started_at = 100.0
    instance.running = True
    monkeypatch.setattr(recorder.time, "perf_counter", lambda: 100.02)
    monkeypatch.setattr(recorder, "active_window_title", lambda: "Test window")
    instance._on_move(10, 20)
    instance._on_move(11, 21)
    assert len(captured) == 1
    assert not hasattr(instance, "keyboard_listener")


def test_pause_blocks_events_and_resume_continues(monkeypatch):
    clock = iter([100.0, 101.0, 103.0, 103.1])
    monkeypatch.setattr(recorder.time, "perf_counter", lambda: next(clock))
    instance = recorder.GlobalMouseRecorder()
    instance.running = True
    instance.started_at = 100.0
    instance.pause()
    instance._emit(recorder.MouseEvent(0.0, "move", 1, 1))
    instance.resume()
    instance._emit(recorder.MouseEvent(instance._time(), "move", 2, 2))
    assert len(instance.events) == 1
    assert instance.events[0].x == 2


def test_warp_is_split_and_never_connected():
    points = [
        (0.000, 10.0, 10.0),
        (0.016, 14.0, 12.0),
        (0.032, 18.0, 14.0),
        (0.048, 900.0, 700.0),
        (0.064, 904.0, 702.0),
    ]
    clean, summary = analysis.clean_and_segment(points)
    grouped = analysis.segments(clean)
    assert summary.warp_count == 1
    assert summary.segment_count == 2
    assert len(grouped) == 2
    assert grouped[0][-1].x == 18.0
    assert grouped[1][0].x == 900.0


def test_long_pause_starts_new_segment_without_deleting_points():
    points = [(0.0, 0.0, 0.0), (0.02, 5.0, 5.0), (1.0, 6.0, 6.0), (1.02, 10.0, 10.0)]
    clean, summary = analysis.clean_and_segment(points)
    assert summary.pause_count == 1
    assert summary.clean_points == len(points)
    assert len(analysis.segments(clean)) == 2


def test_click_test_maps_profile_path_to_exact_endpoints():
    template = [(0.0, 0.0), (0.3, 0.2), (0.7, 0.8), (1.0, 1.0)]
    start = (100.0, 140.0)
    target = (650.0, 420.0)
    path = transform_template(template, start, target, random.Random(42))
    assert path[0] == start
    assert path[-1] == target
    assert len(path) == len(template)


def test_click_test_metrics_report_path_and_overshoot():
    target = (100.0, 0.0)
    path = [(0.0, 0.0), (80.0, 0.0), (125.0, 0.0), (105.0, 0.0), target]
    result = path_metrics(path, target, target_radius=10.0)
    assert result.direct_distance == 100.0
    assert result.travelled_distance > result.direct_distance
    assert result.overshoot_px == 15.0
    assert result.hit_distance_px == 0.0
