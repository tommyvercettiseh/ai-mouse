from __future__ import annotations

from PIL import Image

BG = "#070A13"
SURFACE = "#0E1423"
SURFACE_2 = "#141C30"
BORDER = "#27324B"
TEXT = "#F7F8FC"
MUTED = "#9AA7BE"
PURPLE = "#7C4DFF"
PURPLE_2 = "#B64CFF"
BLUE = "#3E7BFA"
PINK = "#F04A9C"
RED = "#E5484D"
GREEN = "#38D996"


def gradient_image(
    width: int,
    height: int,
    start: tuple[int, int, int] = (31, 19, 74),
    end: tuple[int, int, int] = (8, 12, 28),
) -> Image.Image:
    width, height = max(1, width), max(1, height)
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    for y in range(height):
        v = y / max(1, height - 1)
        for x in range(width):
            u = x / max(1, width - 1)
            mix = min(1.0, max(0.0, (u * 0.62 + v * 0.38)))
            pixels[x, y] = tuple(
                int(start[channel] * (1 - mix) + end[channel] * mix)
                for channel in range(3)
            )
    return image
