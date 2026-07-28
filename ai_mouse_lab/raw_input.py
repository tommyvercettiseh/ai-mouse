from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from typing import Any

RawCallback = Callable[..., None]


class RawMouseListener:
    """Windows Raw Input listener for mouse-only relative dx/dy events."""

    def __init__(self, callback: RawCallback) -> None:
        self.callback = callback
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._hwnd = None
        self._wndproc = None
        self.error: str | None = None
        self.ready = threading.Event()

    @property
    def supported(self) -> bool:
        return os.name == "nt"

    def start(self) -> bool:
        if not self.supported or (self._thread and self._thread.is_alive()):
            return self.supported
        self.error = None
        self.ready.clear()
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_windows, daemon=True)
        self._thread.start()
        self.ready.wait(timeout=1.5)
        return self.ready.is_set() and self.error is None

    def stop(self) -> None:
        self._stop.set()
        if os.name == "nt" and self._hwnd:
            try:
                import ctypes

                ctypes.windll.user32.PostMessageW(self._hwnd, 0x0010, 0, 0)
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def _dispatch(self, clock: float, dx: int, dy: int, device_id: str) -> None:
        try:
            self.callback(clock, dx, dy, device_id)
        except TypeError:
            # Compatibility with older embedded calibration callbacks.
            self.callback(clock, dx, dy)

    def _run_windows(self) -> None:
        if os.name != "nt":
            self.error = "unsupported_platform"
            self.ready.set()
            return
        import ctypes
        from ctypes import wintypes

        WM_INPUT = 0x00FF
        WM_DESTROY = 0x0002
        RID_INPUT = 0x10000003
        RIM_TYPEMOUSE = 0
        RIDEV_INPUTSINK = 0x00000100
        HWND_MESSAGE = wintypes.HWND(-3)

        class RAWINPUTDEVICE(ctypes.Structure):
            _fields_ = [
                ("usUsagePage", wintypes.USHORT),
                ("usUsage", wintypes.USHORT),
                ("dwFlags", wintypes.DWORD),
                ("hwndTarget", wintypes.HWND),
            ]

        class RAWINPUTHEADER(ctypes.Structure):
            _fields_ = [
                ("dwType", wintypes.DWORD),
                ("dwSize", wintypes.DWORD),
                ("hDevice", wintypes.HANDLE),
                ("wParam", wintypes.WPARAM),
            ]

        class BUTTON_STRUCT(ctypes.Structure):
            _fields_ = [("usButtonFlags", wintypes.USHORT), ("usButtonData", wintypes.USHORT)]

        class BUTTON_UNION(ctypes.Union):
            _anonymous_ = ("buttons",)
            _fields_ = [("ulButtons", wintypes.ULONG), ("buttons", BUTTON_STRUCT)]

        class RAWMOUSE(ctypes.Structure):
            _anonymous_ = ("button_union",)
            _fields_ = [
                ("usFlags", wintypes.USHORT),
                ("button_union", BUTTON_UNION),
                ("ulRawButtons", wintypes.ULONG),
                ("lLastX", wintypes.LONG),
                ("lLastY", wintypes.LONG),
                ("ulExtraInformation", wintypes.ULONG),
            ]

        class RAWINPUTDATA(ctypes.Union):
            _fields_ = [("mouse", RAWMOUSE)]

        class RAWINPUT(ctypes.Structure):
            _anonymous_ = ("data",)
            _fields_ = [("header", RAWINPUTHEADER), ("data", RAWINPUTDATA)]

        WNDPROCTYPE = ctypes.WINFUNCTYPE(
            ctypes.c_longlong,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )

        class WNDCLASSW(ctypes.Structure):
            _fields_ = [
                ("style", wintypes.UINT),
                ("lpfnWndProc", WNDPROCTYPE),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
            ]

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        class_name = f"AIMouseRawInput_{id(self)}"

        def window_proc(hwnd: Any, message: int, wparam: Any, lparam: Any) -> int:
            if message == WM_INPUT:
                size = wintypes.UINT(0)
                user32.GetRawInputData(
                    wintypes.HANDLE(lparam), RID_INPUT, None, ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER)
                )
                if size.value:
                    buffer = ctypes.create_string_buffer(size.value)
                    read = user32.GetRawInputData(
                        wintypes.HANDLE(lparam), RID_INPUT, buffer, ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER)
                    )
                    if read == size.value:
                        raw = ctypes.cast(buffer, ctypes.POINTER(RAWINPUT)).contents
                        if raw.header.dwType == RIM_TYPEMOUSE:
                            dx = int(raw.mouse.lLastX)
                            dy = int(raw.mouse.lLastY)
                            if dx or dy:
                                handle_value = ctypes.cast(raw.header.hDevice, ctypes.c_void_p).value or 0
                                self._dispatch(time.perf_counter(), dx, dy, f"raw-{handle_value:x}")
                return 0
            if message == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, message, wparam, lparam)

        self._wndproc = WNDPROCTYPE(window_proc)
        window_class = WNDCLASSW()
        window_class.lpfnWndProc = self._wndproc
        window_class.hInstance = kernel32.GetModuleHandleW(None)
        window_class.lpszClassName = class_name

        atom = user32.RegisterClassW(ctypes.byref(window_class))
        if not atom:
            self.error = "register_window_class_failed"
            self.ready.set()
            return
        hwnd = user32.CreateWindowExW(
            0, class_name, class_name, 0, 0, 0, 0, 0, HWND_MESSAGE, None, window_class.hInstance, None
        )
        if not hwnd:
            self.error = "create_message_window_failed"
            self.ready.set()
            return
        self._hwnd = hwnd

        device = RAWINPUTDEVICE(0x01, 0x02, RIDEV_INPUTSINK, hwnd)
        if not user32.RegisterRawInputDevices(ctypes.byref(device), 1, ctypes.sizeof(RAWINPUTDEVICE)):
            self.error = "register_raw_input_failed"
            self.ready.set()
            user32.DestroyWindow(hwnd)
            return

        self.ready.set()
        message = wintypes.MSG()
        while not self._stop.is_set():
            result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
            if result <= 0:
                break
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))
        if self._hwnd:
            user32.DestroyWindow(self._hwnd)
        self._hwnd = None
