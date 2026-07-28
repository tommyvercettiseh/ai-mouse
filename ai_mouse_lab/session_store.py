from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .environment import capture_environment
from .paths import AIM_LAB_DIR, RECORDINGS_DIR, ROOT, ensure_data_dirs


def _app_version() -> str:
    try:
        return (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        return "unknown"


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, path)


class SessionWriter:
    """Append-only session writer with atomic metadata and recoverable state."""

    def __init__(self, kind: str, context: str = "auto") -> None:
        ensure_data_dirs()
        if kind not in {"recording", "aim_lab"}:
            raise ValueError(f"Unsupported session kind: {kind}")

        self.kind = kind
        self.context = context
        root = RECORDINGS_DIR if kind == "recording" else AIM_LAB_DIR
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
        self.folder = root / f"{context}_{stamp}"
        self.folder.mkdir(parents=True, exist_ok=False)
        self.events_path = self.folder / "events.jsonl"
        self.targets_path = self.folder / "targets.jsonl"
        self.metadata_path = self.folder / "session.json"
        self.summary_path = self.folder / "summary.json"
        self._events = self.events_path.open("a", encoding="utf-8", buffering=1)
        self._targets = None
        if kind == "aim_lab":
            self._targets = self.targets_path.open("a", encoding="utf-8", buffering=1)
        self._lock = threading.Lock()
        self.event_count = 0
        self.target_count = 0
        self.started_at = datetime.now(timezone.utc)
        self.environment = capture_environment(_app_version())
        self._write_metadata(status="recording")

    def _write_metadata(self, status: str) -> None:
        payload = {
            "schema_version": 2,
            "kind": self.kind,
            "context": self.context,
            "status": status,
            "started_at": self.started_at.isoformat(),
            "event_count": self.event_count,
            "target_count": self.target_count,
            "environment": self.environment,
            "privacy": {
                "mouse_only": True,
                "keyboard": False,
                "screenshots": False,
            },
        }
        _atomic_json(self.metadata_path, payload)

    def write_event(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self._events.write(json.dumps(payload, ensure_ascii=False) + "\n")
            self.event_count += 1
            if self.event_count % 2000 == 0:
                self._events.flush()
                os.fsync(self._events.fileno())
                self._write_metadata(status="recording")

    def write_target(self, payload: dict[str, Any]) -> None:
        if self._targets is None:
            raise RuntimeError("Target logging is only available for Aim Lab sessions")
        with self._lock:
            self._targets.write(json.dumps(payload, ensure_ascii=False) + "\n")
            self.target_count += 1

    def finish(self, summary: dict[str, Any] | None = None) -> Path:
        with self._lock:
            if not self._events.closed:
                self._events.flush()
                os.fsync(self._events.fileno())
                self._events.close()
            if self._targets is not None and not self._targets.closed:
                self._targets.flush()
                os.fsync(self._targets.fileno())
                self._targets.close()

        finished = datetime.now(timezone.utc)
        payload = {
            "schema_version": 2,
            "kind": self.kind,
            "context": self.context,
            "started_at": self.started_at.isoformat(),
            "finished_at": finished.isoformat(),
            "duration_s": max(0.0, (finished - self.started_at).total_seconds()),
            "event_count": self.event_count,
            "target_count": self.target_count,
            "environment": self.environment,
            **(summary or {}),
        }
        _atomic_json(self.summary_path, payload)
        self._write_metadata(status="complete")
        return self.folder


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                rows.append(value)
    return rows
