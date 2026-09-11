"""Eight-pose motion study, deliberately separate from the six-frame compiler.

No reference pixels are read or modified. Continuous joint geometry is solved
first; only the diagnostic drawing is rounded to the pixel grid.
"""

import argparse
from dataclasses import asdict, dataclass
from math import hypot, isfinite, sqrt
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

from .config import UniqueLoader
from .errors import AnimationError
from .storage import transaction, write_json


@dataclass(frozen=True)
class Rig:
    ground: int = 104
    hip_x: int = 56
    hip_y: int = 80
    thigh: int = 12
    shin: int = 12
    foot_height: int = 3
    travel_per_frame: int = 3
    duration_ms: int = 120
    shoulder: tuple = (2, -15)
    upper_arm: int = 8
    forearm: int = 8
    hand_drop: int = 14
    arm_swing: float = 0.7
    foot_x: tuple = (6, 3, 0, -3, -6, -4, 0, 5)
    foot_lift: tuple = (0, 0, 0, 0, 2, 6, 8, 5)
    bob: tuple = (0, 1, 0, -1, 0, 1, 0, -1)
    torso: tuple = (-13, -20, 14, 6)
    head: tuple = (-13, -51, 21, -15)
    muzzle: tuple = (13, -33, 28, -22)
    tail: tuple = ((-4, -2), (-22, 8), (-39, 2), (-26, 14), (-1, 7))
    wing: tuple = ((-11, -14), (-26, -21), (-24, -4), (-13, -7))


DEFAULT_RIG = Rig()
PHASES = ("contact", "down", "passing", "up") * 2
BACKGROUND = (24, 34, 56)
NEAR = (245, 165, 65)
FAR = (74, 132, 204)
TORSO = (87, 169, 130)
HEAD = (225, 221, 187)
TAIL = (57, 128, 118)
WING = (141, 112, 173)


def load_rig(path):
    """Strict complete YAML configuration: typos and partial rigs are errors."""
    try:
        data = yaml.load(Path(path).read_text(encoding="utf-8"), Loader=UniqueLoader)
    except (OSError, yaml.YAMLError, RecursionError) as error:
        raise AnimationError(f"Cannot read rig: {error}") from error
    return rig_from_data(data)


def rig_from_data(data):
    """Validate a complete in-memory rig with the same contract as YAML."""
    defaults = asdict(DEFAULT_RIG)
    if not isinstance(data, dict) or data.keys() != defaults.keys():
        raise AnimationError("Rig must contain exactly the documented fields")

    def checked(value, template):
        if isinstance(template, tuple):
            if not isinstance(value, list) or len(value) != len(template):
                raise AnimationError("Invalid rig vector length")
            return tuple(checked(v, t) for v, t in zip(value, template, strict=True))
        if type(value) not in ((int,) if type(template) is int else (int, float)):
            raise AnimationError("Invalid rig numeric type")
        if abs(value) > 1000 or not isfinite(value):
            raise AnimationError("Rig values must be finite and within ±1000")
        return value

    rig = Rig(**{key: checked(data[key], value) for key, value in defaults.items()})
    validate_rig(rig)
    return rig


def validate_rig(rig):
    if not (1 <= rig.travel_per_frame <= 4 and 10 <= rig.duration_ms <= 1000
            and rig.duration_ms % 10 == 0 and 1 <= rig.foot_height <= 8
            and 0 < rig.ground <= 106):
        raise AnimationError("Invalid motion cadence, travel, foot height or ground")
    if rig.foot_lift[:4] != (0, 0, 0, 0) or any(h <= 0 for h in rig.foot_lift[4:]):
        raise AnimationError("Expected four support poses followed by four airborne poses")
    if any(rig.foot_x[i + 1] - rig.foot_x[i] != -rig.travel_per_frame for i in range(3)):
        raise AnimationError("Support foot would slide in world coordinates")
    for name in ("torso", "head", "muzzle"):
        x0, y0, x1, y1 = getattr(rig, name)
        if x0 >= x1 or y0 >= y1:
            raise AnimationError(f"Invalid {name} volume bounds")
    try:
        for i in range(8):
            data = pose(i, rig)
            points = []
            for name in ("torso", "head", "muzzle"):
                x0, y0, x1, y1 = getattr(rig, name)
                points.extend(((rig.hip_x + x0, rig.hip_y + data["bob"] + y0),
                               (rig.hip_x + x1, rig.hip_y + data["bob"] + y1)))
            for name in ("wing", "tail"):
                points.extend((rig.hip_x + x, rig.hip_y + data["bob"] + y)
                              for x, y in getattr(rig, name))
            for collection in ("legs", "arms"):
                for parts in data[collection].values():
                    for key, point in parts.items():
                        if key != "support":
                            points.extend(((point[0] - 4, point[1] - 4),
                                           (point[0] + 6, point[1] + rig.foot_height)))
            if any(not (0 <= round(x) < 112 and 0 <= round(y) < 112) for x, y in points):
                raise AnimationError(f"Pose {i}: mannequin would be clipped")
    except ValueError as error:
        raise AnimationError(str(error)) from error


def joint_between(root, tip, first, second, bend=1):
    """Two-bone inverse kinematics; reject unreachable targets, never stretch."""
    dx, dy = tip[0] - root[0], tip[1] - root[1]
    distance = hypot(dx, dy)
    if first <= 0 or second <= 0 or not abs(first - second) < distance <= first + second:
        raise ValueError("Unreachable two-bone target")
    along = (first * first - second * second + distance * distance) / (2 * distance)
    height = sqrt(max(0, first * first - along * along))
    return (
        root[0] + along * dx / distance + bend * height * dy / distance,
        root[1] + along * dy / distance - bend * height * dx / distance,
    )


def pose(index, rig=DEFAULT_RIG):
    phase = index % 8
    bob = rig.bob[phase]
    hip = (rig.hip_x, rig.hip_y + bob)
    shoulder = (hip[0] + rig.shoulder[0], hip[1] + rig.shoulder[1])
    legs, arms = {}, {}
    for side, offset in (("near", 0), ("far", 4)):
        step = (phase + offset) % 8
        ankle = (rig.hip_x + rig.foot_x[step],
                 rig.ground - rig.foot_height - rig.foot_lift[step])
        legs[side] = {
            "hip": hip,
            "knee": joint_between(hip, ankle, rig.thigh, rig.shin),
            "ankle": ankle,
            "support": step < 4,
        }
        hand = (shoulder[0] - rig.foot_x[step] * rig.arm_swing, shoulder[1] + rig.hand_drop)
        arms[side] = {
            "shoulder": shoulder,
            "elbow": joint_between(shoulder, hand, rig.upper_arm, rig.forearm, bend=-1),
            "hand": hand,
        }
    return {"index": phase, "phase": PHASES[phase], "bob": bob, "legs": legs, "arms": arms}


def draw_pose(data, rig=DEFAULT_RIG, *, skeleton=False, travel=0, width=112):
    image = Image.new("RGB", (width, 112), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.line((0, rig.ground + 1, width, rig.ground + 1), fill=(106, 117, 139))
    for x in range(0, width, 12):
        draw.line((x, rig.ground + 2, x, rig.ground + 5), fill=(106, 117, 139))

    def point(p):
        return round(p[0]) + travel, round(p[1])

    def bone(a, b, color, thickness):
        a, b = point(a), point(b)
        draw.line((a, b), fill=color, width=thickness)
        radius = thickness // 2
        for x, y in (a, b):
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)

    def limb(side, name):
        parts = data[name][side]
        keys = ("hip", "knee", "ankle") if name == "legs" else ("shoulder", "elbow", "hand")
        color = NEAR if side == "near" else FAR
        bone(parts[keys[0]], parts[keys[1]], color, 7 if name == "legs" else 5)
        bone(parts[keys[1]], parts[keys[2]], color, 5)
        if name == "legs":
            x, y = point(parts["ankle"])
            draw.rectangle((x - 3, y, x + 6, y + rig.foot_height), fill=color)
            if parts["support"]:
                draw.line((x - 3, rig.ground + 1, x + 6, rig.ground + 1), fill=color)

    def volume_point(p):
        return point((rig.hip_x + p[0], rig.hip_y + data["bob"] + p[1]))

    def box(bounds):
        return (*volume_point(bounds[:2]), *volume_point(bounds[2:]))

    # A side-view volume hypothesis, not a new approved dragon design.
    draw.polygon([volume_point(p) for p in rig.tail], fill=TAIL)
    limb("far", "legs")
    limb("far", "arms")
    draw.ellipse(box(rig.torso), fill=TORSO)
    draw.polygon([volume_point(p) for p in rig.wing], fill=WING)
    draw.ellipse(box(rig.head), fill=HEAD)
    draw.rectangle(box(rig.muzzle), fill=HEAD)
    limb("near", "legs")
    limb("near", "arms")
    if skeleton:
        for collection, keys in (("legs", ("hip", "knee", "ankle")),
                                 ("arms", ("shoulder", "elbow", "hand"))):
            for parts in data[collection].values():
                points = [point(parts[key]) for key in keys]
                draw.line(points, fill="white", width=1)
                for x, y in points:
                    draw.rectangle((x - 1, y - 1, x + 1, y + 1), fill="white")
    return image


def generate(target, rig=DEFAULT_RIG):
    validate_rig(rig)
    poses = [pose(i, rig) for i in range(8)]
    with transaction(Path(target)) as folder:
        frames = [draw_pose(p, rig) for p in poses]
        sheet = Image.new("RGB", (448, 224), BACKGROUND)
        for i, frame in enumerate(frames):
            frame.save(folder / f"frame_{i:02}.png")
            sheet.paste(frame, ((i % 4) * 112, (i // 4) * 112))
        sheet.resize((896, 448), Image.Resampling.NEAREST).save(folder / "sheet.png")
        for name, sequence, scale in (
            ("walk", frames, 4),
            ("skeleton", [draw_pose(p, rig, skeleton=True) for p in poses], 4),
            ("travel", [draw_pose(pose(i, rig), rig, travel=i * rig.travel_per_frame,
                                   width=224) for i in range(24)], 4),
        ):
            enlarged = [im.resize((im.width * scale, im.height * scale),
                                  Image.Resampling.NEAREST) for im in sequence]
            enlarged[0].save(folder / f"{name}.gif", save_all=True,
                             append_images=enlarged[1:], duration=rig.duration_ms,
                             loop=0, disposal=2, optimize=False)
        write_json(folder / "motion.json", {
            "status": "motion_study_unapproved", "rig": asdict(rig), "poses": poses,
            "note": "Travel resets after three cycles. No approved art or firmware export.",
        })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New directory; existing outputs are never replaced")
    parser.add_argument("--rig", type=Path, help="Complete declarative mannequin YAML")
    args = parser.parse_args()
    try:
        generate(args.output, load_rig(args.rig) if args.rig else DEFAULT_RIG)
    except AnimationError as error:
        parser.exit(2, f"error: {error}\n")
    print(f"Unapproved motion study: {args.output}")


if __name__ == "__main__":
    main()
