"""Create editable 24x24 BMP frames for the rolling egg boot animation."""

from __future__ import annotations

import struct
from pathlib import Path


SIZE = 24
ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets" / "boot"


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

    def ellipse(self, cx: float, cy: float, rx: float, ry: float) -> None:
        for y in range(SIZE):
            for x in range(SIZE):
                distance = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if 0.82 <= distance <= 1.18:
                    self.set(x, y)


def egg(rolling_right: bool, cracked: bool) -> Canvas:
    canvas = Canvas()
    canvas.ellipse(12, 12, 8, 10)
    # Shell markings shift between frames to suggest a roll.
    if rolling_right:
        canvas.line(8, 8, 10, 6)
        canvas.line(14, 15, 17, 17)
        canvas.line(7, 17, 9, 19)
    else:
        canvas.line(15, 7, 17, 9)
        canvas.line(7, 14, 10, 16)
        canvas.line(15, 18, 17, 16)
    if cracked:
        canvas.line(7, 11, 10, 13)
        canvas.line(10, 13, 12, 10)
        canvas.line(12, 10, 15, 14)
        canvas.line(15, 14, 18, 11)
    return canvas


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
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    write_bmp(ASSETS_DIR / "egg_roll_01.bmp", egg(False, False))
    write_bmp(ASSETS_DIR / "egg_roll_02.bmp", egg(True, False))
    write_bmp(ASSETS_DIR / "egg_cracked.bmp", egg(True, True))
    print("Generated rolling egg BMP frames")


if __name__ == "__main__":
    main()
