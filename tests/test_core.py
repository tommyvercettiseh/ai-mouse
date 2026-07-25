from __future__ import annotations

import csv
import json
import random
from pathlib import Path

import ai_mouse_hub.analysis as analysis
import ai_mouse_hub.core as core
import ai_mouse_hub.global_recorder as recorder
from ai_mouse_hub.click_test import path_metrics
from ai_mouse_hub.human_profile import extract_click_templates, generate_target_path, select_template


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


def test_global_recording_is_mouse_only(tmp_path: Path, monkeypatch):
    _redirect_data(tmp_path, monkeypatch)
    monkeypatch.setattr(recorder, "virtual_screen_bounds", lambda: (-1920, 0, 3840, 1080))
    events = [
        recorder.MouseEvent(0.0, "move", -100.0, 200.0, window_title="Browser"),
        recorder.MouseEvent(0.1, "click", 20.0, 220.0, button="Button.left", pressed=True, window_title="Browser"),
        recorder.MouseEvent(0.2, "scroll", 30.0, 230.0, scroll_dy=-1.0, window_title="Game"),
    ]
    folder = recorder.save_global_recording("Gaming", events)
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["recording_scope"] == "global_mouse_only"
    assert metadata["privacy"]["keyboard_recorded"] is False
    assert not (folder / "keyboard_events.csv").exists()
    assert not hasattr(recorder.GlobalMouseRecorder(), "keyboard_listener")


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


def test_warp_is_split_and_never_connected():
    points = [(0.000, 10.0, 10.0), (0.016, 14.0, 12.0), (0.032, 18.0, 14.0),
              (0.048, 900.0, 700.0), (0.064, 904.0, 702.0)]
    clean, summary = analysis.clean_and_segment(points)
    grouped = analysis.segments(clean)
    assert summary.warp_count == 1
    assert len(grouped) == 2


def test_extracts_human_click_template(tmp_path: Path):
    path = tmp_path / "points.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "x", "y", "event_type", "button", "pressed", "scroll_dx", "scroll_dy", "window_title"])
        for i in range(12):
            writer.writerow([i * 0.02, i * 10, (i * i) * 0.8, "move", "", "", 0, 0, "Game"])
        writer.writerow([0.25, 110, 96.8, "click", "Button.left", 1, 0, 0, "Game"])
    templates = extract_click_templates(path, "Gaming")
    assert templates
    assert templates[0].curve_ratio > 1.0
    assert templates[0].click_delay_s >= 0


def test_target_path_preserves_curve_and_ends_near_target():
    template = {
        "points": [[0.0, 0.0, 0.0], [0.35, 0.3, 0.16], [0.7, 0.78, -0.04], [1.0, 1.0, 0.0]],
        "duration_s": 0.5,
        "click_delay_s": 0.08,
        "direct_distance": 300,
        "quality": 1.0,
        "context": "Gaming",
    }
    path, click_delay = generate_target_path(template, (50, 50), (650, 350), random.Random(42), 20)
    assert len(path) == 4
    assert path[1][2] != 50
    assert ((path[-1][1] - 650) ** 2 + (path[-1][2] - 350) ** 2) ** 0.5 <= 20
    assert 0.02 <= click_delay <= 0.22


def test_template_selection_prefers_context():
    templates = [
        {"context": "Browsing", "direct_distance": 200, "quality": 1.0},
        {"context": "Gaming", "direct_distance": 210, "quality": 1.0},
    ]
    selected = select_template(templates, 205, "Gaming", random.Random(42))
    assert selected["context"] == "Gaming"


def test_aim_lab_metrics_include_overshoot_and_click_delay():
    path = [(0.0, 0.0, 0.0), (0.1, 80.0, 0.0), (0.2, 125.0, 0.0), (0.3, 100.0, 0.0)]
    result = path_metrics(path, (100.0, 0.0), 10.0, 0.075)
    assert result.travelled_distance > result.direct_distance
    assert result.overshoot_px == 15.0
    assert result.click_delay_ms == 75.0
