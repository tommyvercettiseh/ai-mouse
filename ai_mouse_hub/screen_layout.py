from __future__ import annotations

import ctypes
from dataclasses import dataclass


@dataclass(frozen=True)
class MonitorInfo:
    index: int
    left: int
    top: int
    width: int
    height: int
    primary: bool = False

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    def contains(self, x: float, y: float) -> bool:
        return self.left <= x < self.right and self.top <= y < self.bottom


def enumerate_monitors() -> list[MonitorInfo]:
    """Return the actual Windows monitor rectangles in virtual-desktop coordinates."""
    try:
        user32 = ctypes.windll.user32
        monitors: list[MonitorInfo] = []

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", ctypes.c_ulong),
            ]

        callback_type = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.POINTER(RECT),
            ctypes.c_double,
        )

        def callback(handle, _hdc, _rect, _data):
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(handle, ctypes.byref(info)):
                rect = info.rcMonitor
                monitors.append(
                    MonitorInfo(
                        index=len(monitors) + 1,
                        left=int(rect.left),
                        top=int(rect.top),
                        width=max(1, int(rect.right - rect.left)),
                        height=max(1, int(rect.bottom - rect.top)),
                        primary=bool(info.dwFlags & 1),
                    )
                )
            return 1

        user32.EnumDisplayMonitors(0, 0, callback_type(callback), 0)
        if monitors:
            monitors.sort(key=lambda item: (item.left, item.top))
            return [
                MonitorInfo(i + 1, m.left, m.top, m.width, m.height, m.primary)
                for i, m in enumerate(monitors)
            ]
    except Exception:
        pass

    return [MonitorInfo(1, 0, 0, 1920, 1080, True)]


def monitor_for_point(monitors: list[MonitorInfo], x: float, y: float) -> MonitorInfo | None:
    for monitor in monitors:
        if monitor.contains(x, y):
            return monitor
    return None
