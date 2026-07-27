from __future__ import annotations

import argparse
import atexit
import subprocess
import sys

import customtkinter as ctk

from .aim_lab_window import AimLabWindow
from .logging_setup import configure_logging
from .main_window import MainWindow
from .paths import AIM_PID_FILE, PID_FILE
from .runtime import clear_pid, write_pid


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Mouse Lab")
    parser.add_argument("--aim-lab", action="store_true", help="Open the balanced Aim Lab")
    args = parser.parse_args()

    configure_logging()
    pid_path = AIM_PID_FILE if args.aim_lab else PID_FILE
    write_pid(pid_path)
    atexit.register(clear_pid, pid_path)
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    if args.aim_lab:
        window = AimLabWindow()
        window.mainloop()
        return

    def open_aim_lab() -> None:
        # A separate process keeps both UIs independent and avoids nested Tk loops.
        subprocess.Popen([sys.executable, "-m", "ai_mouse_lab.app", "--aim-lab"])

    window = MainWindow(open_aim_lab)
    window.mainloop()


if __name__ == "__main__":
    main()
