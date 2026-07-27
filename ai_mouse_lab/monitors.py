from __future__ import annotations

from dataclasses import dataclass

from .models import MonitorInfo


@dataclass(frozen=True)
class VirtualDesktop:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return max(1, self.right - self.left)

    @property
    def height(self) -> int:
        return max(1, self.bottom - self.top)


def discover_monitors() -> list[MonitorInfo]:
    try:
        from screeninfo import get_monitors

        raw = get_monitors()
        monitors = [
            MonitorInfo(
                index=index + 1,
                x=int(item.x),
                y=int(item.y),
                width=int(item.width),
                height=int(item.height),
                primary=bool(getattr(item, "is_primary", False)),
            )
            for index, item in enumerate(raw)
        ]
        if monitors:
            return monitors
    except Exception:
        pass

    return [MonitorInfo(index=1, x=0, y=0, width=1920, height=1080, primary=True)]


def virtual_desktop(monitors: list[MonitorInfo]) -> VirtualDesktop:
    return VirtualDesktop(
        left=min(item.x for item in monitors),
        top=min(item.y for item in monitors),
        right=max(item.right for item in monitors),
        bottom=max(item.bottom for item in monitors),
    )


def monitor_for_point(monitors: list[MonitorInfo], x: float, y: float) -> int | None:
    for monitor in monitors:
        if monitor.contains(x, y):
            return monitor.index
    return None


def screen_to_canvas(
    x: float,
    y: float,
    desktop: VirtualDesktop,
    canvas_width: float,
    canvas_height: float,
    padding: float = 16.0,
) -> tuple[float, float]:
    usable_w = max(1.0, canvas_width - padding * 2)
    usable_h = max(1.0, canvas_height - padding * 2)
    scale = min(usable_w / desktop.width, usable_h / desktop.height)
    offset_x = (canvas_width - desktop.width * scale) / 2.0
    offset_y = (canvas_height - desktop.height * scale) / 2.0
    return (
        offset_x + (x - desktop.left) * scale,
        offset_y + (y - desktop.top) * scale,
    )


def monitor_rect_on_canvas(
    monitor: MonitorInfo,
    desktop: VirtualDesktop,
    canvas_width: float,
    canvas_height: float,
    padding: float = 16.0,
) -> tuple[float, float, float, float]:
    x1, y1 = screen_to_canvas(
        monitor.x, monitor.y, desktop, canvas_width, canvas_height, padding
    )
    x2, y2 = screen_to_canvas(
        monitor.right, monitor.bottom, desktop, canvas_width, canvas_height, padding
    )
    return x1, y1, x2, y2
