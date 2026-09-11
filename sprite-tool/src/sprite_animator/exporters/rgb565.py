def rgb565(red: int, green: int, blue: int) -> int:
    return ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)


def encode(image, byte_order="little", transparency="key", key=(255, 0, 255)):
    from ..errors import AnimationError

    if byte_order not in ("little", "big") or transparency not in ("key", "mask"):
        raise AnimationError("Invalid RGB565 encoding options")
    key_word = rgb565(*key)
    output = bytearray()
    mask = bytearray((image.width * image.height + 7) // 8)
    for index, pixel in enumerate(image.get_flattened_data()):
        if pixel[3] not in (0, 255):
            raise AnimationError("Partial alpha cannot be exported")
        opaque = pixel[3] == 255
        word = rgb565(*pixel[:3]) if opaque else (key_word if transparency == "key" else 0)
        if opaque and transparency == "key" and word == key_word:
            raise AnimationError("Opaque color collides with RGB565 transparency key; use a mask")
        output.extend(word.to_bytes(2, byte_order))
        if opaque:
            mask[index // 8] |= 1 << (7 - index % 8)
    return bytes(output), bytes(mask) if transparency == "mask" else None


def cpp_header(symbol, data: bytes, mask, width, height, duration, byte_order, key_word, frame_count=6):
    def array(name, blob):
        rows = [", ".join(f"0x{b:02X}" for b in blob[i : i + 16]) for i in range(0, len(blob), 16)]
        return f"static const uint8_t {name}[] = {{\n  " + ",\n  ".join(rows) + "\n};\n"

    text = "#pragma once\n#include <stdint.h>\n\n"
    text += f"// RGB565 byte stream, {byte_order}-endian; frame-major, row-major.\n"
    text += f"static constexpr uint16_t {symbol}_width = {width};\n"
    text += f"static constexpr uint16_t {symbol}_height = {height};\n"
    text += f"static constexpr uint8_t {symbol}_frame_count = {frame_count};\n"
    text += f"static constexpr uint16_t {symbol}_duration_ms = {duration};\n"
    text += f"static constexpr uint16_t {symbol}_transparent_key = 0x{key_word:04X};\n"
    text += (
        f"static constexpr bool {symbol}_has_mask = {'true' if mask is not None else 'false'};\n"
    )
    text += array(f"{symbol}_pixels", data)
    if mask is not None:
        text += "// One bit per pixel, MSB first; each frame padded to a byte boundary.\n"
        text += array(f"{symbol}_mask", mask)
    return text
