from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RECORDINGS_DIR = DATA_DIR / "recordings"
AIM_LAB_DIR = DATA_DIR / "aim_lab"
PROFILES_DIR = DATA_DIR / "profiles"
LOGS_DIR = DATA_DIR / "logs"
RUNTIME_DIR = DATA_DIR / "runtime"
CONFIG_DIR = ROOT / "config"
PID_FILE = RUNTIME_DIR / "ai-mouse-lab.pid"
AIM_PID_FILE = RUNTIME_DIR / "aim-lab.pid"
MASTER_PROFILE_FILE = PROFILES_DIR / "master_profile.json"
CALIBRATION_FILE = CONFIG_DIR / "gaming_calibration.json"


def ensure_data_dirs() -> None:
    for path in (
        RECORDINGS_DIR,
        AIM_LAB_DIR,
        PROFILES_DIR,
        LOGS_DIR,
        RUNTIME_DIR,
        CONFIG_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
