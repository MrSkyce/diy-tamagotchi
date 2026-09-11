"""Explicit candidate hip surfaces revealed when a leg leaves the tail root.

Each polygon is authored on the pixel grid, using colors from that model's
approved palette. This does not alter references or infer/draw hidden limbs.
"""

from pathlib import Path

from PIL import Image, ImageDraw

COLORS = {
    "blue_cat": ("#020B23", "#019DFD"),
    "red_dog": ("#07102C", "#F71E1A"),
    "green_mouse": ("#04112A", "#61D541"),
    "purple_salamander": ("#04071B", "#AD25F7"),
}


def build():
    paths = []
    for mascot, (outline, fill) in COLORS.items():
        image = Image.new("RGBA", (112, 112))
        draw = ImageDraw.Draw(image)
        if mascot == "purple_salamander":
            # The wide near leg exposes a second gap against the narrower belly.
            draw.polygon([(65, 84), (74, 83), (76, 88), (71, 91), (65, 88)], fill=outline)
            draw.polygon([(66, 85), (74, 84), (75, 88), (70, 89), (66, 87)], fill=fill)
        draw.polygon(
            [(72, 85), (78, 85), (86, 89), (87, 93), (83, 96), (77, 94), (70, 90)], fill=outline
        )
        draw.polygon(
            [(73, 86), (78, 86), (85, 90), (85, 93), (82, 94), (77, 92), (72, 89)], fill=fill
        )
        path = Path(__file__).parent / mascot / "patches" / "tail_root.png"
        path.parent.mkdir(exist_ok=True)
        if path.exists():
            with Image.open(path) as existing:
                if existing.convert("RGBA").tobytes() != image.tobytes():
                    raise SystemExit(f"Preserve the edited patch {path}; choose a new file")
        else:
            image.save(path, optimize=False, compress_level=9)
        paths.append(path)
    return paths


if __name__ == "__main__":
    for path in build():
        print(path)
