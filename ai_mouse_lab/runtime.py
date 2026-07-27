from __future__ import annotations

import os
from pathlib import Path

from .paths import PID_FILE, ensure_data_dirs


def write_pid(path: Path = PID_FILE) -> None:
    ensure_data_dirs()
    path.write_text(str(os.getpid()), encoding="ascii")


def clear_pid(path: Path = PID_FILE) -> None:
    try:
        if path.exists() and path.read_text(encoding="ascii").strip() == str(os.getpid()):
            path.unlink()
    except Exception:
        pass
