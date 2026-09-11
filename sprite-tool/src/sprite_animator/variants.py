"""Candidate species skins on the deterministic eight-phase walk skeleton.

This separate experiment leaves the approved dragon compiler and assets intact.
Only the design direction is approved: every compiled cycle requires new review.
"""

import argparse
from dataclasses import asdict
from pathlib import Path

from PIL import Image, ImageDraw

from .errors import AnimationError
from .mannequin import BACKGROUND, pose
from .pipeline import generate
from .storage import inventory, transaction, write_json
from .validators import sha256
from .variant_config import load_variant

# Native pixels, anchored at ankle (column 2, row 2). O = outline,
# C = species color. Bottom row stays on the unchanged support plane.
FOOT_PIXELS = {
    "cat": (".OOO...", ".OCO...", ".OCCOO.", "OOCCCCO", ".OCCCO.", "..OOO.."),
    "dog": (".OOO...", ".OCO...", ".OCCOO.", "OOCCCCO", ".OCCCCO", "..OOOO."),
    "mouse": (".OOO..", ".OCO..", ".OCO..", ".OCCO.", "OOCCCO", ".OOOO."),
    "salamander": (".OOO....", ".OCO....", ".OCCO...", "OOCCCOO.", ".OCCCCCO", "..OO.OO."),
    "bird": ("..OCO...", "..OCO...", "..OCO...", ".OCCOO..", "OCOCCCO.", ".O.O.OCO"),
}

# Oversized, rounded cartoon paws. Ankle at column 4 / row 4;
# the curved instep grows upward and forward, never below the support plane.
CARTOON_FOOT_PIXELS = {
    "cartoon_cat": (
        "..OOOO.......", ".OCCCCOO.....", ".OCCCCCCOO...", "OCCCCCCCCCOO.",
        "OCCCCCCCCCCCO", "OCCCCCCCCCCCO", ".OCCCCCOCCCO.", "..OOOOOOOOO.."),
    "cartoon_dog": (
        "..OOOOO.......", ".OCCCCCOO.....", ".OCCCCCCCOO...", "OCCCCCCCCCCOO.",
        "OCCCCCCCCCCCCO", "OCCCCCCCCCCCCO", ".OCCCCCCOCCCO.", "..OOOOOOOOOO.."),
    "cartoon_mouse": (
        "...OOO......", "..OCCCOO....", ".OCCCCCCOO..", "OCCCCCCCCCO.",
        "OCCCCCCCCCCO", "OCCCCCCCCCCO", ".OCCCCCCCCO.", "..OOOOOOOO.."),
    "cartoon_salamander": (
        "..OOOO........", ".OCCCCO.......", ".OCCCCCOOO....", "OCCCCCCCCCOOO.",
        "OCCCCCCCCCCCCO", "OCCCCCCCCCCCCO", ".OCCCCOCCOCCCO", "..OOOO.OO.OOO."),
    "cartoon_bird": (
        "...OOO........", "..OCCCO.......", "..OCCCO.......", ".OCCCCCOOOOO..",
        "OCCCCCCCCCCCO.", "OCCCCCCCCCCCCO", ".OCCCOCCCOCCCO", "..OOO.OOO.OOO."),
}


def draw_refined_foot(image, ankle, style, color, outline, *, continuous_join=False):
    """Replace only the ankle-end raster, never move a solved joint."""
    if style not in FOOT_PIXELS and style not in CARTOON_FOOT_PIXELS:
        raise AnimationError(f"Unknown foot style: {style}")
    x, y = ankle
    cartoon = style in CARTOON_FOOT_PIXELS
    pattern = CARTOON_FOOT_PIXELS[style] if cartoon else FOOT_PIXELS[style]
    anchor = 4 if cartoon else 2
    shin = image.copy() if continuous_join else None
    draw = ImageDraw.Draw(image)
    draw.rectangle((x-6, y-anchor, x+(9 if cartoon else 8), y+3), fill=(0, 0, 0, 0))
    for row, pixels in enumerate(pattern):
        for column, pixel in enumerate(pixels):
            if pixel != ".":
                draw.point((x+column-anchor, y+row-anchor), fill=outline if pixel == "O" else color)
    if shin is not None:
        # Keep the actual slanted tibia rather than a vertical ankle stub.
        # Restore its colored core through the foot's upper outline. Its
        # outer contour only fills transparent pixels, never cuts the foot.
        for py in range(y-anchor, y+1):
            for px in range(x-6, x+10):
                if not (0 <= px < image.width and 0 <= py < image.height):
                    continue
                pixel = shin.getpixel((px, py))
                if pixel == color or (pixel[3] and not image.getpixel((px, py))[3]):
                    image.putpixel((px, py), pixel)


def prepare_parts(source, spec):
    """One native-grid reduction, fixed palette, and explicit component masks."""
    palette = [tuple(bytes.fromhex(c.removeprefix("#"))) for c in spec["palette"]]
    with Image.open(source) as image:
        native = image.convert("RGB").resize((112, 112), Image.Resampling.NEAREST)
    mapped = Image.new("RGBA", native.size)
    pixels = []
    for rgb in native.get_flattened_data():
        r, g, b = rgb
        if r < 45 and 15 < g < 65 and 30 < b < 90 and g > r:
            pixels.append((0, 0, 0, 0))
        else:
            color = min(palette, key=lambda c: sum((a-b)**2 for a, b in zip(c, rgb, strict=True)))
            pixels.append((*color, 255))
    mapped.putdata(pixels)
    parts = {}
    for name, polygon in spec["parts"].items():
        mask = Image.new("1", (112, 112))
        ImageDraw.Draw(mask).polygon([tuple(p) for p in polygon], fill=1)
        part = Image.new("RGBA", (112, 112))
        part.paste(mapped, mask=mask)
        parts[name] = part
    return parts, palette


def render(data, rig, parts, spec, *, layers=False):
    colors = {k: (*bytes.fromhex(v.removeprefix("#")), 255)
              for k, v in spec["colors"].items()}
    bird = spec["body_type"] == "bird"
    images = {}
    for side in ("far", "near"):
        for collection in ("legs", "arms"):
            image = Image.new("RGBA", (112, 112))
            images[f"{side}_{collection}"] = image
            if bird and collection == "arms":
                continue
            draw = ImageDraw.Draw(image)
            node = data[collection][side]
            keys = ("hip", "knee", "ankle") if collection == "legs" else ("shoulder", "elbow", "hand")
            points = [(round(node[k][0]), round(node[k][1])) for k in keys]
            color = colors["foot" if bird and side == "near" else side]
            width = (5 if bird else 9) if collection == "legs" else 7
            for thickness, fill in ((width, colors["outline"]), (width-4 if width > 5 else 3, color)):
                for a, b in zip(points, points[1:], strict=False):
                    draw.line((a, b), fill=fill, width=thickness)
                    radius = thickness // 2
                    for x, y in (a, b):
                        if (x, y) == points[-1] and collection == "legs":
                            continue
                        draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=fill)
            x, y = points[-1]
            if collection == "legs":
                if "foot_style" in spec:
                    if rig.foot_height != 3:
                        raise AnimationError("Refined feet require the three-pixel foot height")
                    draw_refined_foot(image, (x, y), spec["foot_style"], color, colors["outline"],
                                      continuous_join=spec.get("continuous_ankle", False))
                    continue
                # Rounded mammal/amphibian paws: no borrowed dragon claws.
                draw.rounded_rectangle((x-3, y-2, x+6, y+rig.foot_height), radius=2,
                                       fill=colors["outline"])
                draw.rounded_rectangle((x-2, y-1, x+5, y+rig.foot_height-1), radius=1,
                                       fill=color)
                if bird:
                    draw.line((x, y+1, x+6, y+rig.foot_height-1), fill=color, width=2)
    dx = rig.hip_x - spec["source_hip"][0]
    dy = rig.hip_y - spec["source_hip"][1] + data["bob"]
    for name, part in parts.items():
        image = Image.new("RGBA", (112, 112))
        image.alpha_composite(part, (dx, dy))
        images[name] = image
    torso = Image.new("RGBA", (112, 112))
    draw = ImageDraw.Draw(torso)
    hx, hy = rig.hip_x, rig.hip_y + data["bob"]
    rx = 13 if bird else 10
    draw.ellipse((hx-rx, hy-20, hx+12, hy+4), fill=colors["outline"])
    draw.ellipse((hx-rx+2, hy-19, hx+10, hy+2), fill=colors["near"])
    draw.ellipse((hx+2, hy-17, hx+10, hy+1), fill=colors["belly"])
    images["torso"] = torso
    frame = Image.new("RGBA", (112, 112))
    for name in ("tail", "far_legs", "far_arms", "near_legs", "torso", "wing", "head", "near_arms"):
        if name in images:
            frame.alpha_composite(images[name])
    return (frame, images) if layers else frame


def build(config, target):
    config = Path(config).resolve()
    spec, rig, source = load_variant(config)
    parts, palette = prepare_parts(source, spec)
    with transaction(Path(target), inputs=(config, source)) as folder:
        for name, image in parts.items():
            image.save(folder / f"part_{name}.png")
        poses = [pose(i, rig) for i in range(8)]
        frames = [render(data, rig, parts, spec) for data in poses]
        for i, frame in enumerate(frames):
            if frame.getchannel("A").getbbox()[3] != rig.ground+1:
                raise AnimationError(f"Pose {i}: ground mismatch")
            frame.save(folder / f"pose_{i:02}.png")
        travel = []
        for i in range(24):
            image = Image.new("RGB", (224, 112), BACKGROUND)
            draw = ImageDraw.Draw(image)
            draw.line((0, rig.ground+1, 223, rig.ground+1), fill=(106, 117, 139))
            for x in range(0, 224, 12):
                draw.point((x, rig.ground+3), fill=(106, 117, 139))
            image.paste(frames[i % 8], (i*rig.travel_per_frame, 0), frames[i % 8])
            travel.append(image.resize((896, 448), Image.Resampling.NEAREST))
        travel[0].save(folder / "travel.gif", save_all=True, append_images=travel[1:],
                       duration=rig.duration_ms, loop=0, disposal=2, optimize=False)
        write_json(folder / "profile.yaml", {
            "schema_version": 1, "id": "species_walk_study", "animation": "walk",
            "frames": 8, "duration_ms": rig.duration_ms,
            "tracks": {"poses": [{"pose": f"pose_{i:02}"} for i in range(8)]},
        })
        write_json(folder / "mascot.yaml", {
            "schema_version": 1, "id": spec["id"],
            "canvas": {"width": 112, "height": 112, "ground_y": rig.ground},
            "palette": spec["palette"], "animation_profiles": {"walk": "profile.yaml"},
            "layers": [{"id": "rig_skin", "source": "pose_00.png", "anchor": [0, 0],
                        "z_index": 0, "track": "poses",
                        "poses": {f"pose_{i:02}": f"pose_{i:02}.png" for i in range(8)}}],
        })
        write_json(folder / "preparation.json", {
            "status": "candidate", "rig": asdict(rig), "poses": poses,
            "source_sha256": spec["source_sha256"],
            "config_sha256": sha256(config.read_bytes()),
            "compiler_sha256": sha256(Path(__file__).read_bytes()),
            "files": inventory(folder),
            "limitations": ["Only design direction approved; cycle requires review",
                            "Native-grid masks and newly rasterized limbs require review",
                            "Bird proportions differ from approved dragon motion",
                            "No firmware export approval inherited"],
        })
    return Path(target)


def write_gallery(root, target, *, variant_suffix="_rigged"):
    """Read-only comparison of five candidate cycles and the approved dragon."""
    root = Path(root)
    members = [("Chat", "blue_cat"), ("Chien", "red_dog"), ("Souris", "green_mouse"),
               ("Oiseau", "yellow_bird"), ("Salamandre", "purple_salamander"),
               ("Dragon valide", "dragon")]
    frames = {}
    inputs = []
    for _, mascot in members:
        area = "approved" if mascot == "dragon" else "generated"
        suffix = "_rigged" if mascot == "dragon" else variant_suffix
        for direction in ("right", "left"):
            paths = [root / area / f"{mascot}{suffix}" / "walk" / direction / f"frame_{i:02}.png"
                     for i in range(8)]
            inputs.extend(paths)
            frames[mascot, direction] = []
            for path in paths:
                with Image.open(path) as image:
                    frames[mascot, direction].append(image.convert("RGBA"))
    with transaction(Path(target), inputs=inputs) as folder:
        for direction in ("right", "left"):
            sequence = []
            for i in range(24):
                canvas = Image.new("RGB", (448, 384), BACKGROUND)
                draw = ImageDraw.Draw(canvas)
                for n, (label, mascot) in enumerate(members):
                    x, y = (n % 2)*224, (n // 2)*128
                    draw.text((x+8, y+2), label, fill=(235, 240, 255))
                    draw.line((x, y+121, x+223, y+121), fill=(106, 117, 139))
                    for tick in range(0, 224, 12):
                        draw.point((x+tick, y+124), fill=(106, 117, 139))
                    offset = i*3 if direction == "right" else 112-i*3
                    frame = frames[mascot, direction][i % 8]
                    canvas.paste(frame, (x+offset, y+16), frame)
                sequence.append(canvas.resize((896, 768), Image.Resampling.NEAREST))
            sequence[0].save(folder / f"walk-{direction}.gif", save_all=True,
                             append_images=sequence[1:], duration=120, loop=0,
                             disposal=2, optimize=False)
            sequence[0].save(folder / f"contact-{direction}.png")
        write_json(folder / "review.json", {
            "status": "five_candidate_cycles_with_approved_dragon_comparison",
            "inputs": {str(p.relative_to(root)): sha256(p.read_bytes()) for p in inputs},
            "note": "Travel resets after three cycles. No new cycle approval or export.",
        })
    return Path(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    try:
        prepared = build(args.config, args.output)
        print(generate(prepared / "mascot.yaml", args.root))
    except (AnimationError, OSError, ValueError, KeyError) as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    main()
