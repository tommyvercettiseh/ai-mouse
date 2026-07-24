from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RECORDINGS = DATA / "recordings"
PROFILES = DATA / "profiles"
REPORTS = DATA / "stress_lab"
LOGS = DATA / "logs"
for folder in (RECORDINGS, PROFILES, REPORTS, LOGS):
    folder.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Session:
    session_id: str
    folder: Path
    label: str
    created: str
    duration_s: float
    point_count: int
    included: bool


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8", suffix=".tmp") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        temp = Path(handle.name)
    temp.replace(path)


def save_recording(label: str, points: Sequence[tuple[float, float, float]]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = RECORDINGS / f"{stamp}_{label.strip().lower().replace(' ', '_') or 'session'}"
    folder.mkdir(parents=True, exist_ok=False)
    with (folder / "points.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "x", "y"])
        writer.writerows(points)
    duration = max(0.0, points[-1][0] - points[0][0]) if len(points) > 1 else 0.0
    atomic_json(folder / "metadata.json", {
        "session_id": folder.name,
        "label": label.strip() or "Unlabelled",
        "created": datetime.now().isoformat(timespec="seconds"),
        "duration_s": duration,
        "point_count": len(points),
        "included": True,
    })
    return folder


def load_points(path: Path, max_points: int = 5000) -> list[tuple[float, float, float]]:
    if not path.exists():
        return []
    result: list[tuple[float, float, float]] = []
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, csv.Error):
        return []
    stride = max(1, len(rows) // max_points)
    for row in rows[::stride]:
        try:
            values = float(row["timestamp"]), float(row["x"]), float(row["y"])
            if all(math.isfinite(v) for v in values):
                result.append(values)
        except (KeyError, TypeError, ValueError):
            continue
    return result


def list_sessions() -> list[Session]:
    sessions: list[Session] = []
    for meta_path in sorted(RECORDINGS.glob("*/metadata.json"), reverse=True):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
            folder = meta_path.parent
            sessions.append(Session(
                session_id=str(meta.get("session_id") or folder.name),
                folder=folder,
                label=str(meta.get("label") or "Unknown"),
                created=str(meta.get("created") or "Unknown"),
                duration_s=float(meta.get("duration_s") or 0.0),
                point_count=int(meta.get("point_count") or 0),
                included=bool(meta.get("included", True)),
            ))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
    return sessions


def set_included(session: Session, included: bool) -> None:
    path = session.folder / "metadata.json"
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    data["included"] = bool(included)
    atomic_json(path, data)


def normalize_path(points: Sequence[tuple[float, float, float]], count: int = 64) -> list[tuple[float, float]]:
    if len(points) < 2:
        return []
    xy = [(p[1], p[2]) for p in points]
    cumulative = [0.0]
    for a, b in zip(xy, xy[1:]):
        cumulative.append(cumulative[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    total = cumulative[-1]
    if total <= 0:
        return []
    out: list[tuple[float, float]] = []
    cursor = 0
    for i in range(count):
        target = total * i / max(1, count - 1)
        while cursor + 1 < len(cumulative) and cumulative[cursor + 1] < target:
            cursor += 1
        nxt = min(cursor + 1, len(xy) - 1)
        span = cumulative[nxt] - cumulative[cursor]
        ratio = 0.0 if span <= 0 else (target - cumulative[cursor]) / span
        x = xy[cursor][0] + (xy[nxt][0] - xy[cursor][0]) * ratio
        y = xy[cursor][1] + (xy[nxt][1] - xy[cursor][1]) * ratio
        out.append((x, y))
    min_x, max_x = min(x for x, _ in out), max(x for x, _ in out)
    min_y, max_y = min(y for _, y in out), max(y for _, y in out)
    width, height = max(1.0, max_x - min_x), max(1.0, max_y - min_y)
    return [((x - min_x) / width, (y - min_y) / height) for x, y in out]


def _path_features(path: Sequence[tuple[float, float]]) -> dict[str, float]:
    if len(path) < 3:
        return {"length": 0.0, "turning": 0.0, "step_mean": 0.0, "step_std": 0.0}
    steps = [math.hypot(b[0]-a[0], b[1]-a[1]) for a, b in zip(path, path[1:])]
    angles = [math.atan2(b[1]-a[1], b[0]-a[0]) for a, b in zip(path, path[1:])]
    turns = [abs((b-a+math.pi) % (2*math.pi)-math.pi) for a, b in zip(angles, angles[1:])]
    mean = sum(steps) / len(steps)
    variance = sum((s-mean)**2 for s in steps) / len(steps)
    return {"length": sum(steps), "turning": sum(turns), "step_mean": mean, "step_std": math.sqrt(variance)}


def build_master_profile(sessions: Iterable[Session]) -> dict:
    paths: list[list[tuple[float, float]]] = []
    labels: set[str] = set()
    source_ids: list[str] = []
    for session in sessions:
        if not session.included:
            continue
        normalized = normalize_path(load_points(session.folder / "points.csv"))
        if normalized:
            paths.append(normalized)
            labels.add(session.label)
            source_ids.append(session.session_id)
    if not paths:
        raise ValueError("No usable included recordings found")
    features = [_path_features(path) for path in paths]
    profile = {
        "profile_id": "standalone_ai_mouse_profile",
        "profile_version": "0.1.0",
        "created": datetime.now().isoformat(timespec="seconds"),
        "source_count": len(paths),
        "source_ids": source_ids,
        "labels": sorted(labels),
        "features": {
            key: {
                "min": min(item[key] for item in features),
                "mean": sum(item[key] for item in features) / len(features),
                "max": max(item[key] for item in features),
            } for key in features[0]
        },
        "templates": paths[:200],
    }
    atomic_json(PROFILES / "master_profile.json", profile)
    atomic_json(PROFILES / f"master_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", profile)
    return profile


def load_master_profile() -> dict:
    path = PROFILES / "master_profile.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def generate_replay(template: Sequence[tuple[float, float]], rng: random.Random, strength: float = 0.025) -> list[tuple[float, float]]:
    if not template:
        return []
    out: list[tuple[float, float]] = []
    phase = rng.uniform(0, math.tau)
    for index, (x, y) in enumerate(template):
        t = index / max(1, len(template)-1)
        envelope = math.sin(math.pi * t)
        nx = x + envelope * (math.sin(t*math.tau*1.7 + phase) * strength + rng.gauss(0, strength*0.16))
        ny = y + envelope * (math.cos(t*math.tau*1.3 + phase) * strength + rng.gauss(0, strength*0.16))
        out.append((min(1.0, max(0.0, nx)), min(1.0, max(0.0, ny))))
    out[0] = template[0]
    out[-1] = template[-1]
    return out


def similarity(left: Sequence[tuple[float, float]], right: Sequence[tuple[float, float]]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    rms = math.sqrt(sum((a[0]-b[0])**2 + (a[1]-b[1])**2 for a, b in zip(left, right)) / len(left))
    return round(max(0.0, min(100.0, 100.0 * (1.0 - rms / math.sqrt(2.0)))), 2)


def fingerprint(path: Sequence[tuple[float, float]]) -> str:
    payload = ";".join(f"{x:.3f},{y:.3f}" for x, y in path)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def run_stress_test(runs: int = 100, seed: int = 42) -> dict:
    profile = load_master_profile()
    templates = profile.get("templates") or []
    if not templates:
        raise ValueError("Build a master profile first")
    runs = max(10, min(5000, int(runs)))
    rng = random.Random(seed)
    records = []
    fingerprints: dict[str, int] = {}
    for index in range(runs):
        template = templates[rng.randrange(len(templates))]
        strength = rng.uniform(0.012, 0.038)
        replay = generate_replay(template, rng, strength)
        score = similarity(template, replay)
        features = _path_features(replay)
        abrupt = sum(1 for a, b in zip(replay, replay[1:]) if math.hypot(b[0]-a[0], b[1]-a[1]) > 0.16)
        mark = fingerprint(replay)
        fingerprints[mark] = fingerprints.get(mark, 0) + 1
        records.append({"run": index + 1, "similarity": score, "strength": strength, "abrupt_steps": abrupt, **features, "fingerprint": mark})
    duplicate_count = sum(count - 1 for count in fingerprints.values() if count > 1)
    similarities = [r["similarity"] for r in records]
    abrupt_total = sum(r["abrupt_steps"] for r in records)
    similarity_mean = sum(similarities) / len(similarities)
    uniqueness = 100.0 * (1.0 - duplicate_count / runs)
    continuity = max(0.0, 100.0 - abrupt_total * 2.5 / runs)
    variation = min(100.0, 65.0 + len({round(r["strength"], 3) for r in records}) / runs * 35.0)
    overall = round(similarity_mean * 0.35 + uniqueness * 0.25 + continuity * 0.25 + variation * 0.15, 2)
    warnings = []
    if uniqueness < 98: warnings.append("Repeated path fingerprints detected")
    if continuity < 90: warnings.append("Too many abrupt normalized steps")
    if similarity_mean < 85: warnings.append("Generated runs drift too far from recordings")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = REPORTS / stamp
    folder.mkdir(parents=True, exist_ok=False)
    with (folder / "runs.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    report = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "runs": runs,
        "seed": seed,
        "scores": {
            "overall": overall,
            "profile_similarity": round(similarity_mean, 2),
            "natural_variation": round(variation, 2),
            "movement_continuity": round(continuity, 2),
            "repetition_control": round(uniqueness, 2),
        },
        "duplicate_runs": duplicate_count,
        "abrupt_steps": abrupt_total,
        "warnings": warnings,
        "result_folder": str(folder),
    }
    atomic_json(folder / "report.json", report)
    return report
