import pytest
from PIL import Image
from sprite_animator.errors import AnimationError
from sprite_animator.exporters.rgb565 import encode, rgb565


def test_known_primary_colors_and_endianness():
    assert [rgb565(*rgb) for rgb in [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)]] == [
        0xF800,
        0x07E0,
        0x001F,
        0xFFFF,
    ]
    image = Image.new("RGBA", (3, 1))
    image.putdata([(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 0, 0)])
    assert encode(image)[0] == bytes.fromhex("00F8 E007 1FF8")
    assert encode(image, "big")[0] == bytes.fromhex("F800 07E0 F81F")
    data, mask = encode(image, transparency="mask")
    assert data == bytes.fromhex("00F8 E007 0000")
    assert mask == b"\xc0"


def test_key_collision_after_quantization():
    image = Image.new("RGBA", (1, 1), (254, 1, 254, 255))
    with pytest.raises(AnimationError, match="collides"):
        encode(image)
    assert encode(image, transparency="mask")[1] == b"\x80"


def test_mask_padding_across_byte_boundary():
    image = Image.new("RGBA", (9, 1), (0, 0, 0, 255))
    assert encode(image, transparency="mask")[1] == b"\xff\x80"
