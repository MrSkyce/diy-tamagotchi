"""Validate TFT BMP sources and build the compressed W25Q64 asset image."""

from __future__ import annotations

import re
import struct
import zlib
from collections import deque
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
FLASH_BLOB_PATH = PROJECT_ROOT / "include" / "generated_tft_asset_blob.h"
TRANSPARENT_RGB = (255, 0, 255)
MATTE_RED_BLUE_MIN = 100
MATTE_GREEN_MAX = 40
MATTE_RED_BLUE_DELTA_MAX = 40
EXPECTED_ASSET_SIZE = (112, 112)
DRAGON_VISIBLE_PIXEL_RANGE = (5000, 7300)
MAX_ANIMATION_AREA_RATIO = 1.12
MAX_ANIMATION_BOTTOM_DELTA = 3
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


def is_magenta_matte(pixel: tuple[int, int, int]) -> bool:
    """Recognize magenta shades introduced by resampling the old matte."""
    red, green, blue = pixel
    return (
        red >= MATTE_RED_BLUE_MIN
        and blue >= MATTE_RED_BLUE_MIN
        and green <= MATTE_GREEN_MAX
        and abs(red - blue) <= MATTE_RED_BLUE_DELTA_MAX
    )


def normalize_transparent_matte(
        width: int,
        height: int,
        pixels: list[tuple[int, int, int]],
) -> tuple[list[tuple[int, int, int]], int]:
    """Remove only near-magenta pixels connected to transparent source pixels.

    Exact-magenta pixels seed an 8-connected flood fill through matte-like
    colors. This cleans antialiased fringe pixels around both exterior and
    enclosed transparent areas without treating isolated colors inside the
    character as background.
    """
    normalized = list(pixels)
    queue: deque[int] = deque()
    connected = bytearray(len(pixels))
    for index, pixel in enumerate(pixels):
        if pixel == TRANSPARENT_RGB:
            connected[index] = 1
            queue.append(index)

    while queue:
        index = queue.popleft()
        x = index % width
        y = index // width
        for neighbor_y in range(max(0, y - 1), min(height, y + 2)):
            row_start = neighbor_y * width
            for neighbor_x in range(max(0, x - 1), min(width, x + 2)):
                neighbor = row_start + neighbor_x
                if connected[neighbor] or not is_magenta_matte(pixels[neighbor]):
                    continue
                connected[neighbor] = 1
                queue.append(neighbor)

    cleaned = 0
    for index, is_connected in enumerate(connected):
        if is_connected and normalized[index] != TRANSPARENT_RGB:
            normalized[index] = TRANSPARENT_RGB
            cleaned += 1
    return normalized, cleaned


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


FLASH_MAGIC = b"TAMASPR\0"
FLASH_FORMAT_VERSION = 1
FLASH_HEADER_FORMAT = "<8sHHIII"
FLASH_ENTRY_FORMAT = "<IIIHH"


def format_values(values: bytes, digits: int, per_line: int) -> str:
    lines = []
    for start in range(0, len(values), per_line):
        chunk = ", ".join(
            f"0x{value:0{digits}X}" for value in values[start:start + per_line])
        lines.append(f"  {chunk},")
    return "\n".join(lines)


def enum_name(name: str) -> str:
    return name.upper()


def pixels_as_bytes(pixels: list[int]) -> bytes:
    return b"".join(struct.pack("<H", pixel) for pixel in pixels)


def compress_pixels(pixels: list[int]) -> bytes:
    """PackBits-like RGB565 RLE: literal or repeated runs of 1..128 pixels."""
    output = bytearray()
    index = 0
    while index < len(pixels):
        run_length = 1
        while (index + run_length < len(pixels) and
               pixels[index + run_length] == pixels[index] and
               run_length < 128):
            run_length += 1

        if run_length >= 3:
            output.append(0x80 | (run_length - 1))
            output.extend(struct.pack("<H", pixels[index]))
            index += run_length
            continue

        literal_start = index
        index += run_length
        while index < len(pixels) and index - literal_start < 128:
            next_run = 1
            while (index + next_run < len(pixels) and
                   pixels[index + next_run] == pixels[index] and
                   next_run < 128):
                next_run += 1
            if next_run >= 3:
                break
            index += min(next_run, 128 - (index - literal_start))

        literal_length = index - literal_start
        output.append(literal_length - 1)
        output.extend(pixels_as_bytes(
            pixels[literal_start:literal_start + literal_length]))
    return bytes(output)


def decompress_pixels(data: bytes, expected_count: int) -> list[int]:
    """Host-side round-trip validation of the embedded RLE decoder contract."""
    output = []
    offset = 0
    while offset < len(data) and len(output) < expected_count:
        control = data[offset]
        offset += 1
        count = (control & 0x7F) + 1
        if control & 0x80:
            if offset + 2 > len(data):
                raise ValueError("truncated repeated RLE packet")
            pixel = struct.unpack_from("<H", data, offset)[0]
            offset += 2
            output.extend([pixel] * count)
        else:
            byte_count = count * 2
            if offset + byte_count > len(data):
                raise ValueError("truncated literal RLE packet")
            output.extend(struct.unpack_from(f"<{count}H", data, offset))
            offset += byte_count
    if offset != len(data) or len(output) != expected_count:
        raise ValueError("RLE stream does not decode to the expected size")
    return output


def build_flash_image(
        sources: list[Path],
        assets: dict[str, tuple[int, int, list[tuple[int, int, int]]]],
) -> tuple[bytes, int, int]:
    catalog_data = b"".join(asset_name(path).encode("ascii") + b"\0"
                            for path in sources)
    catalog_crc = zlib.crc32(catalog_data) & 0xFFFFFFFF
    header_size = struct.calcsize(FLASH_HEADER_FORMAT)
    entry_size = struct.calcsize(FLASH_ENTRY_FORMAT)
    payload_offset = header_size + entry_size * len(sources)
    entries = bytearray()
    payload = bytearray()
    raw_size = 0

    for path in sources:
        name = asset_name(path)
        width, height, source_pixels = assets[name]
        pixels = [rgb565(*pixel) for pixel in source_pixels]
        raw = pixels_as_bytes(pixels)
        compressed = compress_pixels(pixels)
        if decompress_pixels(compressed, len(pixels)) != pixels:
            raise ValueError(f"{path.name}: RLE round-trip mismatch")
        offset = payload_offset + len(payload)
        entries.extend(struct.pack(
            FLASH_ENTRY_FORMAT, offset, len(compressed),
            zlib.crc32(raw) & 0xFFFFFFFF, width, height))
        payload.extend(compressed)
        raw_size += len(raw)

    body = bytes(entries + payload)
    image_size = header_size + len(body)
    header = struct.pack(
        FLASH_HEADER_FORMAT, FLASH_MAGIC, FLASH_FORMAT_VERSION, len(sources),
        catalog_crc, image_size, zlib.crc32(body) & 0xFFFFFFFF)
    return header + body, catalog_crc, raw_size


def generate() -> None:
    sources = sorted(ASSETS_DIR.glob("*.bmp"))
    if not sources:
        raise ValueError(f"No TFT BMP assets found in {ASSETS_DIR}")

    assets = {}
    cleaned_fringe_pixels = {}
    for path in sources:
        name = asset_name(path)
        width, height, pixels = read_color_bmp(path)
        normalized, cleaned = normalize_transparent_matte(
            width, height, pixels)
        remaining_matte = sum(
            pixel != TRANSPARENT_RGB and is_magenta_matte(pixel)
            for pixel in normalized)
        if remaining_matte:
            raise ValueError(
                f"{path.name}: {remaining_matte} isolated magenta matte "
                "pixels remain after background normalization")
        assets[name] = (width, height, normalized)
        if cleaned:
            cleaned_fringe_pixels[name] = cleaned
    validate_asset_scale(assets)

    flash_image, catalog_crc, raw_size = build_flash_image(sources, assets)
    header = [
        "// Generated by tools/generate_tft_assets.py. Do not edit manually.",
        "#pragma once",
        "",
        "#include <cstddef>",
        "#include <cstdint>",
        "",
        "enum class TftAssetId : uint16_t {",
    ]
    for index, path in enumerate(sources):
        header.append(f"  {enum_name(asset_name(path))} = {index},")
    header.extend([
        f"  COUNT = {len(sources)},",
        "  INVALID = 0xFFFF,",
        "};",
        "",
        f"constexpr uint16_t TFT_ASSET_FORMAT_VERSION = {FLASH_FORMAT_VERSION};",
        f"constexpr uint16_t TFT_ASSET_COUNT = {len(sources)};",
        f"constexpr uint16_t TFT_ASSET_WIDTH = {EXPECTED_ASSET_SIZE[0]};",
        f"constexpr uint16_t TFT_ASSET_HEIGHT = {EXPECTED_ASSET_SIZE[1]};",
        f"constexpr size_t TFT_ASSET_PIXEL_COUNT = "
        f"{EXPECTED_ASSET_SIZE[0] * EXPECTED_ASSET_SIZE[1]};",
        f"constexpr uint16_t TFT_ASSET_TRANSPARENT = "
        f"0x{rgb565(*TRANSPARENT_RGB):04X};",
        f"constexpr uint32_t TFT_ASSET_CATALOG_CRC32 = 0x{catalog_crc:08X};",
        f"constexpr uint32_t TFT_ASSET_FLASH_IMAGE_SIZE = {len(flash_image)};",
        f"constexpr uint32_t TFT_ASSET_RAW_PIXEL_SIZE = {raw_size};",
        "",
    ])

    OUTPUT_PATH.write_text("\n".join(header), encoding="utf-8")

    blob_header = [
        "// Generated by tools/generate_tft_assets.py. Do not edit manually.",
        "#pragma once",
        "",
        "#include <Arduino.h>",
        "",
        "const uint8_t tft_asset_flash_image[] PROGMEM = {",
        format_values(flash_image, 2, 16),
        "};",
        "constexpr size_t tft_asset_flash_image_size =",
        "    sizeof(tft_asset_flash_image);",
        "",
    ]
    FLASH_BLOB_PATH.write_text("\n".join(blob_header), encoding="utf-8")
    ratio = len(flash_image) / raw_size
    print(f"Generated W25Q64 image from {len(sources)} TFT BMP assets: "
          f"{len(flash_image)} bytes ({ratio:.1%} of RGB565)")
    if cleaned_fringe_pixels:
        cleaned_total = sum(cleaned_fringe_pixels.values())
        details = ", ".join(
            f"{name}={count}"
            for name, count in sorted(cleaned_fringe_pixels.items()))
        print(f"Normalized {cleaned_total} background-connected magenta fringe "
              f"pixels across {len(cleaned_fringe_pixels)} assets: {details}")


if BUILD_ENV is not None or __name__ == "__main__":
    generate()
