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


def egg(rotation: int, cracked: bool) -> Canvas:
    canvas = Canvas()
    # Four rotations and a slight vertical bounce make the roll more legible.
    center_y = (12, 11, 12, 13)[rotation]
    canvas.ellipse(12, center_y, 8, 10)
    markings = (
        ((15, 7, 17, 9), (7, 14, 10, 16), (15, 18, 17, 16)),
        ((12, 5, 14, 8), (7, 11, 10, 12), (12, 18, 14, 20)),
        ((7, 7, 9, 9), (14, 14, 17, 16), (7, 18, 9, 16)),
        ((10, 5, 12, 8), (14, 10, 17, 12), (10, 18, 12, 20)),
    )
    for x0, y0, x1, y1 in markings[rotation]:
        canvas.line(x0, y0, x1, y1)
    if cracked:
        canvas.line(7, 11, 10, 13)
        canvas.line(10, 13, 12, 10)
        canvas.line(12, 10, 15, 14)
        canvas.line(15, 14, 18, 11)
    return canvas


def cracked_egg(stage: int) -> Canvas:
    if stage == 0:
        return egg(2, True)

    canvas = Canvas()
    if stage == 1:
        # The two halves pull apart, leaving a bright zig-zag opening.
        canvas.line(4, 18, 4, 11)
        canvas.line(4, 11, 8, 6)
        canvas.line(8, 6, 11, 11)
        canvas.line(11, 11, 8, 14)
        canvas.line(8, 14, 11, 18)
        canvas.line(11, 18, 4, 18)
        canvas.line(20, 18, 20, 11)
        canvas.line(20, 11, 16, 6)
        canvas.line(16, 6, 13, 11)
        canvas.line(13, 11, 16, 14)
        canvas.line(16, 14, 13, 18)
        canvas.line(13, 18, 20, 18)
        canvas.line(11, 5, 12, 3)
        canvas.line(13, 5, 12, 3)
    else:
        # Final burst: the shell halves fall aside and three chips fly out.
        canvas.line(3, 20, 5, 14)
        canvas.line(5, 14, 10, 18)
        canvas.line(10, 18, 8, 22)
        canvas.line(8, 22, 3, 20)
        canvas.line(21, 20, 19, 14)
        canvas.line(19, 14, 14, 18)
        canvas.line(14, 18, 16, 22)
        canvas.line(16, 22, 21, 20)
        canvas.line(11, 8, 12, 5)
        canvas.line(12, 5, 13, 8)
        canvas.line(6, 9, 4, 7)
        canvas.line(18, 9, 20, 7)
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
    for rotation in range(4):
        write_bmp(ASSETS_DIR / f"egg_roll_{rotation + 1:02}.bmp", egg(rotation, False))
    write_bmp(ASSETS_DIR / "egg_crack_01.bmp", cracked_egg(0))
    write_bmp(ASSETS_DIR / "egg_crack_02.bmp", cracked_egg(1))
    write_bmp(ASSETS_DIR / "egg_cracked.bmp", cracked_egg(2))
    print("Generated rolling egg BMP frames")


if __name__ == "__main__":
    main()
