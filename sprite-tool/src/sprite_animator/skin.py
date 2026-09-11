"""Compile an approved art reference onto an approved eight-pose motion rig.

Static components are prepared once on the native grid; articulated limbs are
rasterized from the solved bones, never obtained by shifting whole source legs.
The result is a candidate, not an inherited artistic approval.
"""

import argparse
import os
from pathlib import Path

from PIL import Image, ImageDraw

from .errors import AnimationError
from .mannequin import BACKGROUND, draw_pose, load_rig, pose
from .storage import identifier, inventory, read_json, transaction, write_json
from .validators import sha256


def load_skin(path):
    path = Path(path).resolve()
    spec = read_json(path)
    expected = {"id", "source", "source_sha256", "rig", "motion_approval",
                "art_approval", "source_hip", "palette", "parts"}
    if not isinstance(spec, dict) or spec.keys() != expected:
        raise AnimationError("Invalid skin fields")
    identifier(spec["id"])
    root = path.parent
    inputs = {path}
    for key in ("motion_approval", "art_approval"):
        approval_path = (root / spec[key]).resolve()
        approval = read_json(approval_path)
        status = "approved_motion_only" if key == "motion_approval" else "approved_art_reference_only"
        if approval.get("status") != status or not approval.get("reviewed_by"):
            raise AnimationError(f"Missing {key}")
        inputs.add(approval_path)
        for name, digest in approval["files_sha256"].items():
            member = (root / name).resolve()
            if root not in member.parents or sha256(member.read_bytes()) != digest:
                raise AnimationError(f"Approved reference changed: {name}")
            inputs.add(member)
    source = (root / spec["source"]).resolve()
    rig_path = (root / spec["rig"]).resolve()
    art_approval = read_json(root / spec["art_approval"])
    motion_approval = read_json(root / spec["motion_approval"])
    if (art_approval["files_sha256"].get(spec["source"]) != spec["source_sha256"]
            or spec["rig"] not in motion_approval["files_sha256"]
            or sha256(source.read_bytes()) != spec["source_sha256"]):
        raise AnimationError("Skin inputs must be the approved art and rig")
    rig = load_rig(rig_path)
    inputs.update((source, rig_path))
    palette = [tuple(bytes.fromhex(c.removeprefix("#"))) for c in spec["palette"]]
    if not 1 <= len(palette) <= 253 or any(len(c) != 3 for c in palette):
        raise AnimationError("Invalid skin palette")
    if spec["parts"].keys() != {"head", "wing", "tail"}:
        raise AnimationError("Skin requires head, wing and tail masks")
    for polygon in spec["parts"].values():
        if len(polygon) < 3 or any(len(p) != 2 or any(type(c) is not int or not 0 <= c < 112
                                                   for c in p) for p in polygon):
            raise AnimationError("Invalid native-grid part polygon")
    # Initial asset preparation, never repeated resampling during animation.
    with Image.open(source) as original:
        if original.format != "PNG" or original.width > 4096 or original.height > 4096:
            raise AnimationError("Expected a bounded PNG art reference")
        native = original.convert("RGB").resize((112, 112), Image.Resampling.NEAREST)
    mapped = Image.new("RGBA", native.size)
    pixels = []
    for rgb in native.get_flattened_data():
        r, g, b = rgb
        if r < 45 and 15 < g < 65 and 30 < b < 90 and g > r:
            pixels.append((0, 0, 0, 0))
        else:
            nearest = min(palette, key=lambda c, rgb=rgb: sum((a-b)**2 for a, b in zip(c, rgb, strict=True)))
            pixels.append((*nearest, 255))
    mapped.putdata(pixels)
    parts = {}
    for name, polygon in spec["parts"].items():
        mask = Image.new("1", (112, 112))
        ImageDraw.Draw(mask).polygon([tuple(p) for p in polygon], fill=1)
        part = Image.new("RGBA", (112, 112))
        part.paste(mapped, mask=mask)
        parts[name] = part
    return spec, rig, parts, palette, inputs


def render_pose(data, rig, parts, source_hip, *, layers=False):
    outline = (16, 0, 32, 255)
    bright = (255, 120, 0, 255)
    far = (168, 56, 0, 255)
    claws = (255, 240, 128, 255)
    images = {}

    def limb(side, collection):
        im = Image.new("RGBA", (112, 112))
        draw = ImageDraw.Draw(im)
        node = data[collection][side]
        keys = ("hip", "knee", "ankle") if collection == "legs" else ("shoulder", "elbow", "hand")
        points = [(round(node[key][0]), round(node[key][1])) for key in keys]
        color = bright if side == "near" else far
        for width, fill in ((9 if collection == "legs" else 7, outline),
                            (5 if collection == "legs" else 3, color)):
            for a, b in zip(points, points[1:], strict=False):
                draw.line((a, b), fill=fill, width=width)
                radius = width // 2
                for x, y in (a, b):
                    # Do not extend the ankle below the approved sole.
                    if (x, y) == points[-1] and collection == "legs":
                        continue
                    draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=fill)
        x, y = points[-1]
        if collection == "legs":
            draw.rectangle((x-3, y-2, x+6, y+rig.foot_height), fill=outline)
            draw.rectangle((x-2, y-1, x+5, y+rig.foot_height-1), fill=color)
            for toe in (2, 5):
                draw.line((x+toe, y+1, x+toe, y+rig.foot_height), fill=claws)
        else:
            draw.point((x+1, y+1), fill=claws)
            draw.point((x+2, y), fill=claws)
        images[f"{side}_{collection}"] = im

    for side in ("far", "near"):
        for collection in ("legs", "arms"):
            limb(side, collection)
    dx = rig.hip_x - source_hip[0]
    dy = rig.hip_y - source_hip[1] + data["bob"]
    for name, part in parts.items():
        im = Image.new("RGBA", (112, 112))
        im.alpha_composite(part, (dx, dy))
        images[name] = im
    torso = Image.new("RGBA", (112, 112))
    draw = ImageDraw.Draw(torso)
    hx, hy = rig.hip_x, rig.hip_y + data["bob"]
    draw.ellipse((hx-10, hy-19, hx+12, hy+4), fill=outline)
    draw.ellipse((hx-8, hy-18, hx+10, hy+2), fill=bright)
    draw.ellipse((hx+2, hy-17, hx+10, hy+1), fill=claws)
    images["torso"] = torso
    result = Image.new("RGBA", (112, 112))
    for name in ("tail", "far_legs", "far_arms", "near_legs", "torso", "wing", "head", "near_arms"):
        result.alpha_composite(images[name])
    return (result, images) if layers else result


def prepare(config, target):
    spec, rig, parts, palette, inputs = load_skin(config)
    target = Path(target)
    with transaction(target, inputs=inputs) as folder:
        for name, part in parts.items():
            part.save(folder / f"part_{name}.png")
        poses = [pose(i, rig) for i in range(8)]
        frames = []
        for i, data in enumerate(poses):
            frame = render_pose(data, rig, parts, spec["source_hip"])
            bounds = frame.getchannel("A").getbbox()
            if bounds[3] - 1 != rig.ground:
                raise AnimationError(f"frame_{i}: skin does not preserve ground")
            frame.save(folder / f"pose_{i:02}.png")
            frames.append(frame)
        travel = []
        comparison = Image.new("RGB", (448, 448), BACKGROUND)
        for i, frame in enumerate(frames):
            x, y = (i % 4)*112, (i // 4)*224
            comparison.paste(draw_pose(poses[i], rig), (x, y))
            comparison.paste(frame, (x, y+112), frame)
        comparison.resize((896, 896), Image.Resampling.NEAREST).save(folder / "comparison.png")
        for i in range(24):
            canvas = Image.new("RGB", (224, 112), BACKGROUND)
            draw = ImageDraw.Draw(canvas)
            draw.line((0, rig.ground+1, 223, rig.ground+1), fill=(106, 117, 139))
            for x in range(0, 224, 12):
                draw.line((x, rig.ground+2, x, rig.ground+5), fill=(106, 117, 139))
            canvas.paste(frames[i % 8], (i*rig.travel_per_frame, 0), frames[i % 8])
            travel.append(canvas.resize((896, 448), Image.Resampling.NEAREST))
        travel[0].save(folder / "travel.gif", save_all=True, append_images=travel[1:],
                       duration=rig.duration_ms, loop=0, optimize=False, disposal=2)
        write_json(folder / "profile.yaml", {
            "schema_version": 1, "id": "approved_rig_walk", "animation": "walk",
            "frames": 8, "duration_ms": rig.duration_ms,
            "tracks": {"poses": [{"pose": f"pose_{i:02}"} for i in range(8)]},
        })
        write_json(folder / "mascot.yaml", {
            "schema_version": 1, "id": spec["id"],
            "canvas": {"width": 112, "height": 112, "ground_y": rig.ground},
            "palette": ["#"+bytes(c).hex().upper() for c in palette],
            "animation_profiles": {"walk": "profile.yaml"},
            "layers": [{"id": "rig_skin", "source": "pose_00.png", "anchor": [0, 0],
                        "z_index": 0, "track": "poses",
                        "poses": {f"pose_{i:02}": f"pose_{i:02}.png" for i in range(8)}}],
        })
        write_json(folder / "preparation.json", {
            "status": "candidate_skin_on_approved_motion", "poses": poses,
            "inputs": {os.path.relpath(p, Path(config).resolve().parent): sha256(p.read_bytes())
                       for p in sorted(inputs)},
            "compiler_sha256": sha256(Path(__file__).read_bytes()),
            "files": inventory(folder),
            "limitations": ["Native-grid reduction and palette mapping require art review",
                            "Body and articulated limbs are newly rasterized candidate artwork",
                            "No production export approval is inherited"],
        })
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        print(prepare(args.config, args.output))
    except (AnimationError, OSError, ValueError, KeyError) as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    main()
