"""Author the small hidden hip surface exposed by translating the pilot's legs.

This explicit pixel patch is a candidate, not an approved change to the dragon.
Only existing palette colors and integer polygons are used. The output is never
placed in assets/tft and the production references remain untouched.
"""

from pathlib import Path

from PIL import Image, ImageDraw


def build():
    path = Path(__file__).parent / "patches" / "hip.png"
    image = Image.new("RGBA", (112, 112))
    draw = ImageDraw.Draw(image)
    # Dark edge under the belly; most of this patch is hidden by the body/legs.
    draw.polygon(
        [(57, 86), (73, 86), (76, 92), (73, 97), (66, 100), (59, 98), (55, 92)], fill="#040B2B"
    )
    draw.polygon(
        [(58, 86), (72, 86), (74, 92), (71, 96), (65, 98), (60, 96), (57, 91)], fill="#FCB936"
    )
    draw.polygon([(58, 85), (72, 85), (73, 90), (69, 94), (62, 95), (58, 91)], fill="#FDEA5C")
    path.parent.mkdir(exist_ok=True)
    if path.exists():
        with Image.open(path) as existing:
            if existing.convert("RGBA").tobytes() != image.tobytes():
                raise SystemExit(
                    "Existing patch differs; preserve manual edits and choose a new file"
                )
        return path
    image.save(path, optimize=False, compress_level=9)
    return path


if __name__ == "__main__":
    print(build())
