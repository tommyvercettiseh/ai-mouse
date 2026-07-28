from __future__ import annotations

import hashlib
import json
import os
import platform
from typing import Any

from .monitors import discover_monitors


def _windows_pointer_settings() -> dict[str, Any]:
    result: dict[str, Any] = {
        "pointer_speed": None,
        "enhance_pointer_precision": None,
    }
    if os.name != "nt":
        return result
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Mouse") as key:
            speed, _ = winreg.QueryValueEx(key, "MouseSensitivity")
            threshold1, _ = winreg.QueryValueEx(key, "MouseThreshold1")
            threshold2, _ = winreg.QueryValueEx(key, "MouseThreshold2")
        result["pointer_speed"] = int(speed)
        result["enhance_pointer_precision"] = not (
            str(threshold1) == "0" and str(threshold2) == "0"
        )
    except Exception:
        pass
    return result


def capture_environment(app_version: str) -> dict[str, Any]:
    monitors = [monitor.to_dict() for monitor in discover_monitors()]
    layout_json = json.dumps(monitors, sort_keys=True, separators=(",", ":"))
    return {
        "app_version": app_version,
        "profile_schema": 2,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "monitor_layout": monitors,
        "monitor_layout_hash": hashlib.sha256(layout_json.encode("utf-8")).hexdigest()[:16],
        "windows_pointer": _windows_pointer_settings(),
        "raw_input_expected": os.name == "nt",
    }
