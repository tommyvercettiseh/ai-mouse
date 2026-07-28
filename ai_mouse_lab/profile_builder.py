from __future__ import annotations

import json
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


def _recording_context(folder: Path) -> str:
    summary_path = folder / "summary.json"
    if not summary_path.exists():
        return "auto"
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        return str(summary.get("dominant_input_mode") or summary.get("context") or "auto")
    except Exception:
        return "auto"


def _extract_recording_data() -> tuple[
    list[dict[str, Any]], set[str], int, list[dict[str, Any]], list[dict[str, Any]]
]:
    monitors = discover_monitors()
    default_diagonal = statistics.fmean(item.diagonal for item in monitors)
    movements: list[dict[str, Any]] = []
    clicks: list[dict[str, Any]] = []
    scrolls: list[dict[str, Any]] = []
    contexts: set[str] = set()
    transitions = 0

    for folder in _session_dirs(RECORDINGS_DIR):
        rows = read_jsonl(folder / "events.jsonl")
        if not rows:
            continue
        context = _recording_context(folder)
        contexts.add(context)

        path: list[tuple[float, float, float]] = []
        path_monitors: list[int | None] = []
        last_t: float | None = None

        def flush() -> None:
            nonlocal path, path_monitors, transitions
            if len(path) >= 3:
                transition = len({item for item in path_monitors if item is not None}) > 1
                metric = analyze_movement(path, default_diagonal, transition)
                if metric is not None:
                    if transition:
                        transitions += 1
                    movements.append(
                        {
                            "context": context,
                            **metric.to_dict(),
                            "normalized_trace": normalize_trace(path),
                        }
                    )
            path = path[-1:] if path else []
            path_monitors = path_monitors[-1:] if path_monitors else []

        for row in rows:
            row_type = row.get("type")
            if row_type == "click":
                if row.get("pressed"):
                    flush()
                elif row.get("hold_ms") is not None:
                    clicks.append(
                        {
                            "context": context,
                            "button": row.get("button", "unknown"),
                            "hold_ms": float(row.get("hold_ms") or 0),
                            "moved_while_held_px": float(row.get("moved_while_held_px") or 0),
                        }
                    )
                continue
            if row_type == "scroll":
                scrolls.append(
                    {
                        "context": context,
                        "direction": row.get("direction", "unknown"),
                        "step_magnitude": float(row.get("step_magnitude") or 0),
                        "burst_id": int(row.get("burst_id") or 0),
                        "gap_ms": row.get("gap_from_previous_ms"),
                        "t": float(row.get("t") or 0),
                    }
                )
                continue
            if row_type != "move":
                continue
            try:
                t, x, y = float(row["t"]), float(row["x"]), float(row["y"])
            except (KeyError, TypeError, ValueError):
                continue
            if last_t is not None and t - last_t >= 0.35:
                flush()
            path.append((t, x, y))
            path_monitors.append(row.get("monitor"))
            last_t = t
        flush()

    return movements, contexts, transitions, clicks, scrolls


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
            "moved_while_held_px": _stats(
                [float(row["moved_while_held_px"]) for row in rows]
            ),
        }
        for button, rows in by_button.items()
    }


def _scroll_profile(scrolls: list[dict[str, Any]]) -> dict[str, Any]:
    bursts: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in scrolls:
        bursts[(str(row.get("context", "auto")), int(row.get("burst_id", 0)))].append(row)

    burst_lengths = [len(rows) for rows in bursts.values() if rows]
    burst_durations = [
        max(0.0, float(rows[-1]["t"]) - float(rows[0]["t"])) * 1000.0
        for rows in bursts.values()
        if rows
    ]
    gaps = [float(row["gap_ms"]) for row in scrolls if row.get("gap_ms") is not None]
    magnitudes = [float(row["step_magnitude"]) for row in scrolls]
    direction_counts: dict[str, int] = defaultdict(int)
    for row in scrolls:
        direction_counts[str(row.get("direction", "unknown"))] += 1

    reversals = 0
    for rows in bursts.values():
        ordered = sorted(rows, key=lambda row: float(row.get("t", 0)))
        for left, right in zip(ordered, ordered[1:]):
            if left.get("direction") != right.get("direction"):
                reversals += 1

    return {
        "event_count": len(scrolls),
        "burst_count": len(bursts),
        "direction_counts": dict(direction_counts),
        "step_magnitude": _stats(magnitudes),
        "gap_within_burst_ms": _stats(gaps),
        "events_per_burst": _stats([float(value) for value in burst_lengths]),
        "burst_duration_ms": _stats(burst_durations),
        "direction_reversals": reversals,
        "usage": "scroll_logic_only",
    }


def build_master_profile() -> dict[str, Any]:
    ensure_data_dirs()
    movements, contexts, transitions, clicks, scrolls = _extract_recording_data()
    aim_targets = _extract_aim_targets()

    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for movement in movements:
        key = f"{movement['context']}:{movement['distance_bucket']}"
        buckets[key].append(movement)
    for target in aim_targets:
        key = f"aim_lab:{target.get('size_bucket', 'unknown')}:{target.get('distance_bucket', 'unknown')}"
        buckets[key].append(target)

    bucket_stats: dict[str, Any] = {}
    numeric_fields = (
        "duration_ms",
        "mean_speed_px_s",
        "peak_speed_px_s",
        "efficiency",
        "correction_count",
        "reaction_ms",
        "movement_ms",
        "click_delay_ms",
        "click_hold_ms",
        "overshoot_px",
        "end_offset_px",
    )
    for key, rows in buckets.items():
        result: dict[str, Any] = {"count": len(rows)}
        for field in numeric_fields:
            values = [float(row[field]) for row in rows if row.get(field) is not None]
            if values:
                result[field] = _stats(values)
        bucket_stats[key] = result

    templates = [
        {
            "context": row["context"],
            "distance_bucket": row["distance_bucket"],
            "metrics": {
                key: row[key]
                for key in (
                    "duration_ms",
                    "mean_speed_px_s",
                    "peak_speed_px_s",
                    "efficiency",
                    "correction_count",
                )
            },
            "points": row["normalized_trace"],
        }
        for row in movements[-400:]
        if row.get("normalized_trace")
    ]

    movement_score = min(1.0, len(movements) / 500.0) * 35.0
    aim_score = min(1.0, len(aim_targets) / 300.0) * 35.0
    context_score = min(1.0, len(contexts) / 2.0) * 15.0
    transition_score = min(1.0, transitions / 30.0) * 15.0
    progress = round(movement_score + aim_score + context_score + transition_score)

    profile = {
        "schema_version": 2,
        "name": "Hesse Mouse Profile",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile_progress_percent": int(max(0, min(100, progress))),
        "source_counts": {
            "recording_movements": len(movements),
            "aim_lab_targets": len(aim_targets),
            "monitor_transitions": transitions,
            "click_releases": len(clicks),
            "scroll_events": len(scrolls),
            "contexts": sorted(contexts),
        },
        "buckets": bucket_stats,
        "templates": templates,
        "click_profile": _click_profile(clicks),
        "scroll_profile": _scroll_profile(scrolls),
        "profile_separation": {
            "movement": "trace_shape_speed_corrections",
            "click": "button_hold_and_drag",
            "scroll": "scroll_logic_only",
        },
        "privacy": {
            "mouse_only": True,
            "keyboard": False,
            "screenshots": False,
        },
    }
    MASTER_PROFILE_FILE.write_text(
        json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return profile


def load_profile_progress() -> int:
    if not MASTER_PROFILE_FILE.exists():
        return 0
    try:
        data = json.loads(MASTER_PROFILE_FILE.read_text(encoding="utf-8"))
        return int(data.get("profile_progress_percent", 0))
    except Exception:
        return 0
