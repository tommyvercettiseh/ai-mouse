from __future__ import annotations

import customtkinter as ctk

from .gaming import GamingCalibration, save_calibration
from .raw_input import RawMouseListener
from .theme import BG, GREEN, MUTED, PURPLE, SURFACE, TEXT


class CalibrationWindow(ctk.CTkToplevel):
    """Optional one-rotation calibration; not required for raw-count logging."""

    def __init__(self, master) -> None:
        super().__init__(master)
        self.title("Gaming 360° Calibration")
        self.geometry("520x360")
        self.configure(fg_color=BG)
        self.resizable(False, False)
        self.total_x = 0
        self.total_y = 0
        self.listener = RawMouseListener(self._raw)
        self.capturing = False

        card = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=20)
        card.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(card, text="360° Calibration", text_color=TEXT, font=("Segoe UI", 25, "bold")).pack(anchor="w", padx=24, pady=(24, 6))
        ctk.CTkLabel(
            card,
            text="Zet de game op een ander scherm. Klik Start, draai exact één volledige horizontale ronde en klik Stop. Alleen raw muis-delta's worden gemeten.",
            text_color=MUTED,
            wraplength=430,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 18))
        self.value = ctk.CTkLabel(card, text="0 raw counts", text_color=TEXT, font=("Segoe UI", 30, "bold"))
        self.value.pack(pady=16)
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=18)
        ctk.CTkButton(row, text="Start", fg_color=PURPLE, command=self.start_capture, height=44, corner_radius=12).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(row, text="Stop + Save", fg_color=GREEN, text_color="#06130D", command=self.stop_capture, height=44, corner_radius=12).pack(side="left", expand=True, fill="x", padx=(6, 0))
        self.protocol("WM_DELETE_WINDOW", self.close)

    def _raw(self, _clock: float, dx: int, dy: int) -> None:
        if not self.capturing:
            return
        self.total_x += dx
        self.total_y += dy
        self.after(0, lambda: self.value.configure(text=f"{abs(self.total_x):,.0f} raw counts"))

    def start_capture(self) -> None:
        self.total_x = 0
        self.total_y = 0
        self.capturing = True
        self.listener.start()
        self.value.configure(text="0 raw counts")

    def stop_capture(self) -> None:
        self.capturing = False
        self.listener.stop()
        counts = abs(float(self.total_x))
        if counts >= 50:
            save_calibration(GamingCalibration(counts_per_360_x=counts))
            self.value.configure(text=f"Saved: {counts:,.0f} / 360°", text_color=GREEN)
        else:
            self.value.configure(text="Te weinig beweging", text_color="#E5484D")

    def close(self) -> None:
        self.listener.stop()
        self.destroy()
