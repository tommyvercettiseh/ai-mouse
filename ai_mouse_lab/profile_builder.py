from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .metrics import analyze_movement, normalize_trace
from .monitors import discover_monitors
from .paths import AIM_LAB_DIR, MASTER_PROFILE_FILE, RECORDINGS_DIR, ensure_data_dirs
from .session_store import read_jsonl


def _quantile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower = int(index)
    upper = min(len(ordered) - 1, lower + 1)
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _stats(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "median": round(statistics.median(values), 5) if values else None,
        "mean": round(statistics.fmean(values), 5) if values else None,
        "p10": round(_quantile(values, 0.10), 5) if values else None,
        "p25": round(_quantile(values, 0.25), 5) if values else None,
        "p75": round(_quantile(values, 0.75), 5) if values else None,
        "p90": round(_quantile(values, 0.90), 5) if values else None,
    }


def _session_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted((path for path in root.iterdir() if path.is_dir()), key=lambda p: p.name)


def _load_summary(folder: Path) -> dict[str, Any]:
    try:
        return json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def _extract_recording_data() -> dict[str, Any]:
    monitors = discover_monitors()
    default_diagonal = statistics.fmean(item.diagonal for item in monitors)
    movements: list[dict[str, Any]] = []
    gaming_segments: list[dict[str, Any]] = []
    clicks: list[dict[str, Any]] = []
    scrolls: list[dict[str, Any]] = []
    session_medians: list[float] = []
    contexts: set[str] = set()
    transitions = 0
    complete_sessions = 0
    excluded_gaming_sessions = 0

    for folder in _session_dirs(RECORDINGS_DIR):
        rows = read_jsonl(folder / "events.jsonl")
        summary = _load_summary(folder)
        if not rows or not summary:
            continue
        complete_sessions += 1
        context = str(summary.get("dominant_input_mode") or summary.get("context") or "auto")
        contexts.add(context)

        path: list[tuple[float, float, float]] = []
        path_monitors: list[int | None] = []
        session_speeds: list[float] = []
        raw_path: list[tuple[float, float, float]] = []
        raw_x = raw_y = 0.0
        last_t: float | None = None

        def flush_absolute() -> None:
            nonlocal path, path_monitors, transitions
            if len(path) >= 3:
                transition = len({item for item in path_monitors if item is not None}) > 1
                metric = analyze_movement(path, default_diagonal, transition)
                if metric is not None:
                    if transition:
                        transitions += 1
                    row = {
                        "context": "absolute",
                        **metric.to_dict(),
                        "normalized_trace": normalize_trace(path),
                    }
                    movements.append(row)
                    session_speeds.append(float(row["mean_speed_px_s"]))
            path = path[-1:] if path else []
            path_monitors = path_monitors[-1:] if path_monitors else []

        gaming_allowed = bool(summary.get("gaming_quality", {}).get("included_in_gaming_profile"))
        if summary.get("event_types", {}).get("raw_move") and not gaming_allowed:
            excluded_gaming_sessions += 1

        for row in rows:
            row_type = row.get("type")
            if row_type == "click":
                if row.get("pressed"):
                    flush_absolute()
                elif row.get("hold_ms") is not None:
                    clicks.append({
                        "context": context,
                        "button": row.get("button", "unknown"),
                        "hold_ms": float(row.get("hold_ms") or 0),
                        "drag_distance_px": float(row.get("drag_distance_px") or 0),
                    })
                continue
            if row_type == "scroll":
                scrolls.append({
                    "context": context,
                    "direction": row.get("direction", "unknown"),
                    "step_magnitude": abs(float(row.get("dy") or row.get("dx") or 0)),
                    "t": float(row.get("t") or 0),
                })
                continue
            if row_type == "raw_move" and gaming_allowed:
                try:
                    t = float(row["t"])
                    raw_x += float(row["dx"])
                    raw_y += float(row["dy"])
                    raw_path.append((t, raw_x, raw_y))
                except (KeyError, TypeError, ValueError):
                    pass
                continue
            if row_type != "move":
                continue
            try:
                t, x, y = float(row["t"]), float(row["x"]), float(row["y"])
            except (KeyError, TypeError, ValueError):
                continue
            if last_t is not None and t - last_t >= 0.35:
                flush_absolute()
            path.append((t, x, y))
            path_monitors.append(row.get("monitor"))
            last_t = t
        flush_absolute()

        if gaming_allowed and len(raw_path) >= 3:
            metric = analyze_movement(raw_path, max(1.0, math.hypot(raw_x, raw_y)))
            if metric is not None:
                gaming_segments.append({
                    "context": "gaming_raw",
                    **metric.to_dict(),
                    "normalized_trace": normalize_trace(raw_path),
                })
        if session_speeds:
            session_medians.append(statistics.median(session_speeds))

    return {
        "movements": movements,
        "gaming_segments": gaming_segments,
        "clicks": clicks,
        "scrolls": scrolls,
        "contexts": contexts,
        "transitions": transitions,
        "session_medians": session_medians,
        "complete_sessions": complete_sessions,
        "excluded_gaming_sessions": excluded_gaming_sessions,
    }


def _extract_aim_targets() -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for folder in _session_dirs(AIM_LAB_DIR):
        targets.extend(read_jsonl(folder / "targets.jsonl"))
    return [row for row in targets if row.get("click_hit")]


def _click_profile(clicks: list[dict[str, Any]]) -> dict[str, Any]:
    by_button: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in clicks:
        by_button[str(row.get("button", "unknown"))].append(row)
    return {
        button: {
            "count": len(rows),
            "hold_ms": _stats([float(row["hold_ms"]) for row in rows]),
            "drag_distance_px": _stats([float(row["drag_distance_px"]) for row in rows]),
        }
        for button, rows in by_button.items()
    }


def _scroll_profile(scrolls: list[dict[str, Any]]) -> dict[str, Any]:
    if not scrolls:
        return {"event_count": 0, "usage": "scroll_logic_only"}
    ordered = sorted(scrolls, key=lambda row: float(row.get("t", 0)))
    bursts: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for row in ordered:
        if current and float(row["t"]) - float(current[-1]["t"]) > 0.22:
            bursts.append(current)
            current = []
        current.append(row)
    if current:
        bursts.append(current)
    directions: dict[str, int] = defaultdict(int)
    for row in ordered:
        directions[str(row.get("direction", "unknown"))] += 1
    reversals = sum(
        1
        for burst in bursts
        for left, right in zip(burst, burst[1:])
        if left.get("direction") != right.get("direction")
    )
    return {
        "event_count": len(ordered),
        "burst_count": len(bursts),
        "direction_counts": dict(directions),
        "step_magnitude": _stats([float(row["step_magnitude"]) for row in ordered]),
        "events_per_burst": _stats([float(len(burst)) for burst in bursts]),
        "burst_duration_ms": _stats([
            max(0.0, float(burst[-1]["t"]) - float(burst[0]["t"])) * 1000.0
            for burst in bursts
        ]),
        "direction_reversals": reversals,
        "usage": "scroll_logic_only",
    }


def _stability_score(session_medians: list[float]) -> float:
    if len(session_medians) < 3:
        return min(1.0, len(session_medians) / 3.0) * 0.4
    mean = statistics.fmean(session_medians)
    if mean <= 0:
        return 0.0
    cv = statistics.pstdev(session_medians) / mean
    return max(0.0, min(1.0, 1.0 - cv / 0.45))


def build_master_profile() -> dict[str, Any]:
    ensure_data_dirs()
    data = _extract_recording_data()
    movements = data["movements"]
    gaming_segments = data["gaming_segments"]
    clicks = data["clicks"]
    scrolls = data["scrolls"]
    aim_targets = _extract_aim_targets()

    all_movements = movements + gaming_segments
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for movement in all_movements:
        buckets[f"{movement['context']}:{movement['distance_bucket']}"] .append(movement)
    for target in aim_targets:
        buckets[f"aim_lab:{target.get('size_bucket', 'unknown')}:{target.get('distance_bucket', 'unknown')}"] .append(target)

    bucket_stats: dict[str, Any] = {}
    numeric_fields = (
        "duration_ms", "mean_speed_px_s", "peak_speed_px_s", "efficiency",
        "correction_count", "reaction_ms", "movement_ms", "click_delay_ms",
        "click_hold_ms", "overshoot_px", "end_offset_px",
    )
    for key, rows in buckets.items():
        result: dict[str, Any] = {"count": len(rows)}
        for field in numeric_fields:
            values = [float(row[field]) for row in rows if row.get(field) is not None]
            if values:
                result[field] = _stats(values)
        bucket_stats[key] = result

    templates = [{
        "context": row["context"],
        "distance_bucket": row["distance_bucket"],
        "metrics": {key: row[key] for key in (
            "duration_ms", "mean_speed_px_s", "peak_speed_px_s", "efficiency", "correction_count"
        )},
        "points": row["normalized_trace"],
    } for row in all_movements[-600:] if row.get("normalized_trace")]

    coverage = min(1.0, len(buckets) / 12.0)
    volume = min(1.0, (len(all_movements) + len(aim_targets)) / 700.0)
    stability = _stability_score(data["session_medians"])
    quality = min(1.0, data["complete_sessions"] / 5.0)
    progress = round((coverage * 0.35 + volume * 0.25 + stability * 0.25 + quality * 0.15) * 100)

    profile = {
        "schema_version": 3,
        "name": "Hesse Mouse Profile",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile_progress_percent": int(max(0, min(100, progress))),
        "profile_components": {
            "coverage_percent": round(coverage * 100),
            "volume_percent": round(volume * 100),
            "stability_percent": round(stability * 100),
            "data_quality_percent": round(quality * 100),
        },
        "source_counts": {
            "absolute_movements": len(movements),
            "gaming_raw_segments": len(gaming_segments),
            "aim_lab_targets": len(aim_targets),
            "monitor_transitions": data["transitions"],
            "click_releases": len(clicks),
            "scroll_events": len(scrolls),
            "complete_sessions": data["complete_sessions"],
            "excluded_gaming_sessions": data["excluded_gaming_sessions"],
            "contexts": sorted(data["contexts"]),
        },
        "buckets": bucket_stats,
        "templates": templates,
        "click_profile": _click_profile(clicks),
        "scroll_profile": _scroll_profile(scrolls),
        "profile_separation": {
            "absolute": "desktop_pointer_coordinates",
            "gaming_raw": "relative_dx_dy_only_after_quality_gate",
            "click": "button_hold_and_drag",
            "scroll": "scroll_logic_only",
        },
        "privacy": {"mouse_only": True, "keyboard": False, "screenshots": False},
    }
    temp = MASTER_PROFILE_FILE.with_suffix(".json.tmp")
    temp.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(MASTER_PROFILE_FILE)
    return profile


def load_profile_progress() -> int:
    if not MASTER_PROFILE_FILE.exists():
        return 0
    try:
        data = json.loads(MASTER_PROFILE_FILE.read_text(encoding="utf-8"))
        return int(data.get("profile_progress_percent", 0))
    except Exception:
        return 0
