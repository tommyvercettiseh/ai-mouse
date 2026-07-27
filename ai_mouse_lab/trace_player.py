from __future__ import annotations

from pathlib import Path

from .session_store import read_jsonl


def load_trace(folder: Path) -> list[tuple[float, float, float]]:
    rows = read_jsonl(folder / "events.jsonl")
    points: list[tuple[float, float, float]] = []
    for row in rows:
        if row.get("type") != "move":
            continue
        try:
            points.append((float(row["t"]), float(row["x"]), float(row["y"])))
        except (KeyError, TypeError, ValueError):
            continue
    return points


def latest_session(root: Path) -> Path | None:
    if not root.exists():
        return None
    folders = [path for path in root.iterdir() if path.is_dir()]
    return max(folders, key=lambda path: path.stat().st_mtime) if folders else None
