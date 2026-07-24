from __future__ import annotations

import json
import random
from pathlib import Path

import ai_mouse_hub.core as core


def test_normalize_and_replay():
    points = [(0.0, 0.0, 0.0), (0.1, 50.0, 25.0), (0.2, 100.0, 100.0)]
    normalized = core.normalize_path(points, count=16)
    assert len(normalized) == 16
    replay = core.generate_replay(normalized, random.Random(42))
    assert replay[0] == normalized[0]
    assert replay[-1] == normalized[-1]
    assert 0 < core.similarity(normalized, replay) <= 100


def test_recording_profile_and_stress(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(core, "DATA", tmp_path)
    monkeypatch.setattr(core, "RECORDINGS", tmp_path / "recordings")
    monkeypatch.setattr(core, "PROFILES", tmp_path / "profiles")
    monkeypatch.setattr(core, "REPORTS", tmp_path / "stress_lab")
    monkeypatch.setattr(core, "LOGS", tmp_path / "logs")
    for folder in (core.RECORDINGS, core.PROFILES, core.REPORTS, core.LOGS):
        folder.mkdir(parents=True, exist_ok=True)

    points = [(i * 0.01, float(i * 3), float(i * 2 + (i % 5))) for i in range(150)]
    core.save_recording("Browsing", points)
    sessions = core.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].point_count == 150

    profile = core.build_master_profile(sessions)
    assert profile["source_count"] == 1
    assert (core.PROFILES / "master_profile.json").exists()

    first = core.run_stress_test(25, 42)
    second = core.run_stress_test(25, 42)
    assert 0 <= first["scores"]["overall"] <= 100
    assert first["scores"] == second["scores"]
    report_path = Path(first["result_folder"]) / "report.json"
    assert json.loads(report_path.read_text(encoding="utf-8"))["runs"] == 25
