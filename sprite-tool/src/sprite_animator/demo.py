"""Small hand-specified geometric fixtures, never substitutes for approved mascots."""

from pathlib import Path

import yaml
from PIL import Image

from .errors import AnimationError
from .storage import transaction

COLORS = {
    ".": (0, 0, 0, 0),
    "K": (24, 34, 56, 255),
    "B": (40, 144, 224, 255),
    "Y": (248, 208, 48, 255),
    "R": (224, 80, 64, 255),
}


def pixels(rows):
    assert len({len(row) for row in rows}) == 1
    image = Image.new("RGBA", (len(rows[0]), len(rows)))
    image.putdata([COLORS[c] for row in rows for c in row])
    return image


def fixture(folder: Path, mascot="demo_biped", quadruped=False):
    """Create a new fixture directory; no overwrite of any existing file."""
    if folder.exists():
        raise AnimationError(f"Fixture destination already exists: {folder}")
    folder.mkdir(parents=True)
    body = [
        ".KKKKKKKKKK.",
        "KBBBBBBBBBBK",
        "KBBBBBBBBBBK",
        "KBBBBBBBBBBK",
        "KBBBBBBBBBBK",
        "KBBBBBBBBBBK",
        ".KKKKKKKKKK.",
    ]
    head = [".KKKKK", "KYYYYK", "KYYKYK", "KYYYYK", ".KKKKK"]
    poses = {
        "forward": [
            "..KK...",
            "..RK...",
            "...RK..",
            "...RK..",
            "...RK..",
            "....RK.",
            "....RKK",
            "....KKK",
        ],
        "neutral": [
            "..KK...",
            "..RK...",
            "..RK...",
            "..RK...",
            "..RK...",
            "..RK...",
            "..RKK..",
            "..KKK..",
        ],
        "backward": [
            "..KK...",
            "..RK...",
            ".RK....",
            ".RK....",
            ".RK....",
            "RK.....",
            "RKK....",
            "KKK....",
        ],
    }
    pixels(body).save(folder / "body.png")
    pixels(head).save(folder / "head.png")
    for name, rows in poses.items():
        pixels(rows).save(folder / f"leg_{name}.png")
    # Fixed foot height while the head uses a parent-relative cyclic offset.
    near = ["forward", "forward", "neutral", "backward", "backward", "neutral"]
    far = near[3:] + near[:3]
    profile = {
        "schema_version": 1,
        "id": "quadruped" if quadruped else "biped",
        "animation": "walk",
        "frames": 6,
        "duration_ms": 120,
        "tracks": {
            "near_leg": [{"pose": p} for p in near],
            "far_leg": [{"pose": p} for p in far],
            "head": [{"offset": [0, y]} for y in [0, 0, 1, 0, 1, 0]],
        },
    }
    (folder / "profile.yaml").write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    layers = [
        {"id": "body", "source": "body.png", "anchor": [9, 14], "z_index": 20},
        {
            "id": "head",
            "source": "head.png",
            "anchor": [8, -4],
            "parent": "body",
            "track": "head",
            "z_index": 30,
        },
    ]
    for name, x, track, z in [("near_leg", 15, "near_leg", 40), ("far_leg", 11, "far_leg", 10)]:
        layers.append(
            {
                "id": name,
                "source": "leg_neutral.png",
                "anchor": [x, 20],
                "z_index": z,
                "track": track,
                "poses": {pose: f"leg_{pose}.png" for pose in poses},
            }
        )
    if quadruped:
        for name, x, track, z in [("rear_near", 7, "far_leg", 40), ("rear_far", 5, "near_leg", 10)]:
            layers.append(
                {
                    "id": name,
                    "source": "leg_neutral.png",
                    "anchor": [x, 20],
                    "z_index": z,
                    "track": track,
                    "poses": {pose: f"leg_{pose}.png" for pose in poses},
                }
            )
    data = {
        "schema_version": 1,
        "id": mascot,
        "canvas": {"width": 32, "height": 32, "ground_y": 27},
        "palette": ["#182238", "#2890E0", "#F8D030", "#E05040"],
        "animation_profiles": {"walk": "profile.yaml"},
        "layers": layers,
    }
    (folder / "mascot.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return folder / "mascot.yaml"


def init_demo(root: Path):
    root = root.resolve()
    if root.exists():
        raise AnimationError(f"Demo root must be a new directory: {root}")
    with transaction(root) as temporary:
        fixture(temporary / "mascots" / "demo_biped")
        fixture(temporary / "mascots" / "demo_quadruped", "demo_quadruped", True)
    return root
