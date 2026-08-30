"""Create an original 40x40 outline-dragon draft as editable BMP sprites."""

from __future__ import annotations

import struct
from pathlib import Path


SIZE = 40
ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets" / "sprites"


class Canvas:
    def __init__(self) -> None:
        self.pixels = [[False for _ in range(SIZE)] for _ in range(SIZE)]

    def set(self, x: int, y: int) -> None:
        if 0 <= x < SIZE and 0 <= y < SIZE:
            self.pixels[y][x] = True

    def line(self, x0: int, y0: int, x1: int, y1: int) -> None:
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        error = dx + dy
        while True:
            self.set(x0, y0)
            if (x0, y0) == (x1, y1):
                return
            doubled = 2 * error
            if doubled >= dy:
                error += dy
                x0 += sx
            if doubled <= dx:
                error += dx
                y0 += sy

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, thickness: float = 0.16) -> None:
        for y in range(max(0, int(cy - ry - 1)), min(SIZE, int(cy + ry + 2))):
            for x in range(max(0, int(cx - rx - 1)), min(SIZE, int(cx + rx + 2))):
                distance = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if 1 - thickness <= distance <= 1 + thickness:
                    self.set(x, y)

    def fill_ellipse(self, cx: float, cy: float, rx: float, ry: float) -> None:
        for y in range(max(0, int(cy - ry)), min(SIZE, int(cy + ry + 1))):
            for x in range(max(0, int(cx - rx)), min(SIZE, int(cx + rx + 1))):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1:
                    self.set(x, y)


def base_dragon() -> Canvas:
    canvas = Canvas()
    # Horns and head: a large airy outline, not a filled silhouette.
    canvas.line(10, 9, 11, 3)
    canvas.line(11, 3, 15, 9)
    canvas.line(25, 9, 29, 3)
    canvas.line(29, 3, 30, 10)
    canvas.ellipse(20, 17, 14, 12)

    # Small body, feet, wing and curled tail.
    canvas.ellipse(20, 34, 8, 4)
    canvas.line(14, 35, 12, 38)
    canvas.line(12, 38, 17, 38)
    canvas.line(26, 35, 28, 38)
    canvas.line(28, 38, 33, 38)
    canvas.line(13, 28, 7, 25)
    canvas.line(7, 25, 9, 33)
    canvas.line(9, 33, 14, 31)
    canvas.line(27, 30, 33, 33)
    canvas.line(33, 33, 36, 30)
    canvas.line(36, 30, 35, 26)
    canvas.line(35, 26, 32, 26)
    canvas.line(32, 26, 31, 29)
    return canvas


def open_eyes(canvas: Canvas) -> None:
    canvas.ellipse(15, 17, 3, 4)
    canvas.ellipse(25, 17, 3, 4)
    canvas.fill_ellipse(15, 18, 1.2, 2.2)
    canvas.fill_ellipse(25, 18, 1.2, 2.2)


def face(canvas: Canvas, mood: str) -> None:
    if mood == "blink":
        canvas.line(12, 17, 18, 17)
        canvas.line(22, 17, 28, 17)
    elif mood == "sleeping":
        canvas.line(12, 17, 18, 18)
        canvas.line(22, 18, 28, 17)
        canvas.line(31, 13, 34, 13)
        canvas.line(33, 11, 34, 13)
    elif mood == "sick":
        canvas.line(12, 14, 18, 20)
        canvas.line(18, 14, 12, 20)
        canvas.line(22, 14, 28, 20)
        canvas.line(28, 14, 22, 20)
    else:
        open_eyes(canvas)

    # Broad, isolated mouths remain readable on the real 128x64 OLED.
    if mood == "happy":
        canvas.line(14, 21, 17, 26)
        canvas.line(17, 26, 23, 26)
        canvas.line(23, 26, 26, 21)
    elif mood == "hungry":
        canvas.line(16, 21, 24, 21)
        canvas.line(16, 21, 16, 27)
        canvas.line(24, 21, 24, 27)
        canvas.line(16, 27, 24, 27)
    elif mood in {"sad", "sick"}:
        canvas.line(14, 26, 17, 21)
        canvas.line(17, 21, 23, 21)
        canvas.line(23, 21, 26, 26)
    else:
        canvas.ellipse(20, 23, 4, 2)


def write_bmp(path: Path, canvas: Canvas) -> None:
    row_bytes = ((SIZE + 31) // 32) * 4
    pixel_offset = 14 + 40 + 8
    image_size = row_bytes * SIZE
    header = bytearray(b"BM")
    header.extend(struct.pack("<IHHI", pixel_offset + image_size, 0, 0, pixel_offset))
    header.extend(struct.pack("<IiiHHIIiiII", 40, SIZE, SIZE, 1, 1, 0,
                              image_size, 0, 0, 2, 0))
    header.extend(b"\x00\x00\x00\x00\xFF\xFF\xFF\x00")
    pixels = bytearray()
    for y in range(SIZE - 1, -1, -1):
        row = bytearray(row_bytes)
        for x in range(SIZE):
            if canvas.pixels[y][x]:
                row[x // 8] |= 0x80 >> (x % 8)
        pixels.extend(row)
    path.write_bytes(header + pixels)


def main() -> None:
    moods = {
        "dragon_idle1": "idle",
        "dragon_idle2": "idle",
        "dragon_blink": "blink",
        "dragon_happy": "happy",
        "dragon_hungry": "hungry",
        "dragon_sad": "sad",
        "dragon_sick": "sick",
        "dragon_sleeping": "sleeping",
    }
    for name, mood in moods.items():
        dragon = base_dragon()
        face(dragon, mood)
        if name == "dragon_idle2":
            dragon.line(34, 26, 37, 24)
        write_bmp(ASSETS_DIR / f"{name}.bmp", dragon)
    print("Generated original outline dragon draft BMP sprites")


if __name__ == "__main__":
    main()
