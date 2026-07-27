from __future__ import annotations

import importlib.util
import json
import sys

from .paths import ROOT, ensure_data_dirs


def run() -> dict:
    ensure_data_dirs()
    required = ("customtkinter", "PIL", "pynput", "screeninfo")
    missing = [name for name in required if importlib.util.find_spec(name) is None]
    files = (
        ROOT / "VERSION",
        ROOT / "turbo-project.json",
        ROOT / "Start Project.bat",
        ROOT / "ai_mouse_lab" / "app.py",
    )
    missing_files = [str(path.relative_to(ROOT)) for path in files if not path.exists()]
    return {
        "status": "ok" if not missing and not missing_files else "error",
        "python": sys.version.split()[0],
        "missing_dependencies": missing,
        "missing_files": missing_files,
    }


def main() -> None:
    result = run()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "ok" else 1)


if __name__ == "__main__":
    main()
