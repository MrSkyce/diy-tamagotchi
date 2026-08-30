"""Scale a directory of 1-bit BMP sprites with nearest-neighbor pixels."""

from __future__ import annotations

import importlib.util
import struct
import sys
from pathlib import Path


def load_generator_module():
    generator_path = Path(__file__).with_name("generate_sprites.py")
    specification = importlib.util.spec_from_file_location("sprite_generator", generator_path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def write_bmp(path: Path, width: int, height: int, pixels: list[bool]) -> None:
    source_row_bytes = (width + 7) // 8
    row_bytes = ((width + 31) // 32) * 4
    pixel_offset = 14 + 40 + 8
    image_size = row_bytes * height
    header = bytearray(b"BM")
    header.extend(struct.pack("<IHHI", pixel_offset + image_size, 0, 0, pixel_offset))
    header.extend(struct.pack("<IiiHHIIiiII", 40, width, height, 1, 1, 0,
                              image_size, 0, 0, 2, 0))
    header.extend(b"\x00\x00\x00\x00\xFF\xFF\xFF\x00")

    rows = bytearray()
    for y in range(height - 1, -1, -1):
        row = bytearray(source_row_bytes)
        for x in range(width):
            if pixels[y * width + x]:
                row[x // 8] |= 0x80 >> (x % 8)
        rows.extend(row)
        rows.extend(b"\x00" * (row_bytes - source_row_bytes))
    path.write_bytes(header + rows)


def main(source_dir: Path, backup_dir: Path, target_size: int) -> None:
    generator = load_generator_module()
    sources = sorted(source_dir.glob("*.bmp"))
    if not sources:
        raise ValueError(f"No BMP sprites found in {source_dir}")
    backup_dir.mkdir(parents=True, exist_ok=True)

    for path in sources:
        width, height, pixels = generator.read_bmp(path)
        (backup_dir / path.name).write_bytes(path.read_bytes())
        scaled = [
            pixels[(y * height // target_size) * width + (x * width // target_size)]
            for y in range(target_size)
            for x in range(target_size)
        ]
        write_bmp(path, target_size, target_size, scaled)
        print(f"Scaled {path.name}: {width}x{height} -> {target_size}x{target_size}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]))
