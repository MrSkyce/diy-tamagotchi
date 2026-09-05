"""Convert indexed-color TFT BMP sources into RGB565 data and 1-bit masks."""

from __future__ import annotations

import re
import struct
from pathlib import Path


try:
    Import("env")
except NameError:
    BUILD_ENV = None
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
else:
    BUILD_ENV = env
    PROJECT_ROOT = Path(BUILD_ENV["PROJECT_DIR"])

ASSETS_DIR = PROJECT_ROOT / "assets" / "tft"
OUTPUT_PATH = PROJECT_ROOT / "include" / "generated_tft_assets.h"
TRANSPARENT_RGB = (255, 0, 255)
EXPECTED_ASSET_SIZE = (112, 112)
DRAGON_VISIBLE_PIXEL_RANGE = (5000, 7300)
MAX_ANIMATION_AREA_RATIO = 1.12
MAX_ANIMATION_BOTTOM_DELTA = 2
ANIMATION_GROUPS = {
    "idle": ("dragon_idle1", "dragon_idle2"),
    "clean": ("dragon_clean_01", "dragon_clean_02"),
    "food": ("dragon_food_01", "dragon_food_02"),
    "medicine": ("dragon_medicine_01", "dragon_medicine_02"),
    "play": ("dragon_play_01", "dragon_play_02"),
    "sleep": ("dragon_sleep_01", "dragon_sleep_02"),
    "sleep_refuse": ("dragon_sleep_refuse_01", "dragon_sleep_refuse_02"),
    "tired": ("dragon_tired_01", "dragon_tired_02"),
    "walk_left": ("dragon_walk_left_01", "dragon_walk_left_02"),
    "walk_right": ("dragon_walk_right_01", "dragon_walk_right_02"),
}


def asset_name(path: Path) -> str:
    return re.sub(r"[^a-z0-9_]", "_", path.stem.lower())


def read_color_bmp(path: Path) -> tuple[int, int, list[tuple[int, int, int]]]:
    data = path.read_bytes()
    if len(data) < 54 or data[:2] != b"BM":
        raise ValueError(f"{path.name}: expected a BMP file")

    pixel_offset = struct.unpack_from("<I", data, 10)[0]
    dib_size = struct.unpack_from("<I", data, 14)[0]
    width, height = struct.unpack_from("<ii", data, 18)
    planes, bits_per_pixel = struct.unpack_from("<HH", data, 26)
    compression = struct.unpack_from("<I", data, 30)[0]
    colors_used = struct.unpack_from("<I", data, 46)[0]
    if (dib_size < 40 or planes != 1 or bits_per_pixel not in (8, 24) or
            compression != 0 or width <= 0 or height == 0):
        raise ValueError(
            f"{path.name}: expected an uncompressed 8-bit or 24-bit BMP")

    palette = []
    if bits_per_pixel == 8:
        palette_size = colors_used or 256
        palette_offset = 14 + dib_size
        if palette_offset + palette_size * 4 > pixel_offset:
            raise ValueError(f"{path.name}: invalid color palette")
        for index in range(palette_size):
            blue, green, red, _ = data[palette_offset + index * 4:
                                       palette_offset + index * 4 + 4]
            palette.append((red, green, blue))

    absolute_height = abs(height)
    bytes_per_pixel = bits_per_pixel // 8
    row_bytes = (width * bytes_per_pixel + 3) & ~3
    if pixel_offset + row_bytes * absolute_height > len(data):
        raise ValueError(f"{path.name}: pixel data is incomplete")

    pixels = []
    for y in range(absolute_height):
        source_y = absolute_height - 1 - y if height > 0 else y
        row_start = pixel_offset + source_y * row_bytes
        for x in range(width):
            if bits_per_pixel == 8:
                color_index = data[row_start + x]
                if color_index >= len(palette):
                    raise ValueError(f"{path.name}: invalid palette index")
                pixels.append(palette[color_index])
            else:
                start = row_start + x * 3
                blue, green, red = data[start:start + 3]
                pixels.append((red, green, blue))
    return width, absolute_height, pixels


def rgb565(red: int, green: int, blue: int) -> int:
    return ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)


def mask_bytes(width: int, height: int,
               pixels: list[tuple[int, int, int]]) -> list[int]:
    row_bytes = (width + 7) // 8
    output = [0] * (row_bytes * height)
    for y in range(height):
        for x in range(width):
            if pixels[y * width + x] != TRANSPARENT_RGB:
                output[y * row_bytes + x // 8] |= 0x80 >> (x % 8)
    return output


def validate_asset_scale(
        assets: dict[str, tuple[int, int, list[tuple[int, int, int]]]]) -> None:
    visible_pixels = {}
    visible_bottoms = {}
    for name, (width, height, pixels) in assets.items():
        if (width, height) != EXPECTED_ASSET_SIZE:
            raise ValueError(
                f"{name}: expected {EXPECTED_ASSET_SIZE[0]}x"
                f"{EXPECTED_ASSET_SIZE[1]}, got {width}x{height}")
        visible_pixels[name] = sum(
            pixel != TRANSPARENT_RGB for pixel in pixels)
        visible_rows = [
            index // width for index, pixel in enumerate(pixels)
            if pixel != TRANSPARENT_RGB
        ]
        if not visible_rows:
            raise ValueError(f"{name}: asset has no visible pixels")
        visible_bottoms[name] = max(visible_rows)

    minimum, maximum = DRAGON_VISIBLE_PIXEL_RANGE
    for name, area in visible_pixels.items():
        if name.startswith("dragon_") and not minimum <= area <= maximum:
            raise ValueError(
                f"{name}: visible area {area} is outside the normalized "
                f"dragon range {minimum}..{maximum}")

    for group, names in ANIMATION_GROUPS.items():
        missing = [name for name in names if name not in visible_pixels]
        if missing:
            raise ValueError(f"{group}: missing animation assets {missing}")
        areas = [visible_pixels[name] for name in names]
        ratio = max(areas) / min(areas)
        if ratio > MAX_ANIMATION_AREA_RATIO:
            raise ValueError(
                f"{group}: frame scale ratio {ratio:.3f} exceeds "
                f"{MAX_ANIMATION_AREA_RATIO:.2f} ({areas})")
        bottoms = [visible_bottoms[name] for name in names]
        bottom_delta = max(bottoms) - min(bottoms)
        if bottom_delta > MAX_ANIMATION_BOTTOM_DELTA:
            raise ValueError(
                f"{group}: ground-line delta {bottom_delta}px exceeds "
                f"{MAX_ANIMATION_BOTTOM_DELTA}px ({bottoms})")


def format_values(values: list[int], digits: int, per_line: int) -> str:
    lines = []
    for start in range(0, len(values), per_line):
        chunk = ", ".join(
            f"0x{value:0{digits}X}" for value in values[start:start + per_line])
        lines.append(f"  {chunk},")
    return "\n".join(lines)


def generate() -> None:
    sources = sorted(ASSETS_DIR.glob("*.bmp"))
    if not sources:
        raise ValueError(f"No TFT BMP assets found in {ASSETS_DIR}")

    assets = {}
    for path in sources:
        assets[asset_name(path)] = read_color_bmp(path)
    validate_asset_scale(assets)

    header = [
        "// Generated by tools/generate_tft_assets.py. Do not edit manually.",
        "#pragma once",
        "",
        "#include <Arduino.h>",
        "",
    ]
    for path in sources:
        name = asset_name(path)
        width, height, pixels = assets[name]
        colors = [rgb565(*pixel) for pixel in pixels]
        mask = mask_bytes(width, height, pixels)
        header.extend([
            f"constexpr uint16_t {name}_width = {width};",
            f"constexpr uint16_t {name}_height = {height};",
            f"const uint16_t {name}_pixels[] PROGMEM = {{",
            format_values(colors, 4, 10),
            "};",
            f"const uint8_t {name}_mask[] PROGMEM = {{",
            format_values(mask, 2, 12),
            "};",
            "",
        ])

    OUTPUT_PATH.write_text("\n".join(header), encoding="utf-8")
    print(f"Generated {OUTPUT_PATH.relative_to(PROJECT_ROOT)} "
          f"from {len(sources)} TFT BMP assets")


if BUILD_ENV is not None or __name__ == "__main__":
    generate()
