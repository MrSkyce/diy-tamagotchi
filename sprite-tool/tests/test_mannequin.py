import json
from dataclasses import asdict
from hashlib import sha256
from math import dist, sqrt
from pathlib import Path

import pytest
import yaml
from PIL import Image
from sprite_animator.errors import AnimationError
from sprite_animator.mannequin import Rig, draw_pose, generate, joint_between, load_rig, pose


def test_bones_never_stretch_and_support_is_on_ground():
    rig = Rig()
    for i in range(24):
        data = pose(i)
        assert any(leg["support"] for leg in data["legs"].values())
        for leg in data["legs"].values():
            for a, b, length in (("hip", "knee", rig.thigh), ("knee", "ankle", rig.shin)):
                assert dist(leg[a], leg[b]) == pytest.approx(length)
                raster_length = dist(tuple(map(round, leg[a])), tuple(map(round, leg[b])))
                assert abs(raster_length - length) <= sqrt(2)
            bottom = leg["ankle"][1] + rig.foot_height
            assert bottom == rig.ground if leg["support"] else bottom < rig.ground
        for arm in data["arms"].values():
            assert dist(arm["shoulder"], arm["elbow"]) == pytest.approx(8)
            assert dist(arm["elbow"], arm["hand"]) == pytest.approx(8)


def test_world_support_does_not_slide_including_cycle_boundary():
    for side in ("near", "far"):
        for i in range(23):
            a, b = pose(i)["legs"][side], pose(i + 1)["legs"][side]
            if a["support"] and b["support"]:
                assert a["ankle"][0] + i * 3 == b["ankle"][0] + (i + 1) * 3
    assert pose(0) == pose(8)
    assert len({draw_pose(pose(i)).tobytes() for i in range(8)}) == 8


def test_unreachable_target_rejected():
    with pytest.raises(ValueError):
        joint_between((0, 0), (50, 0), 12, 12)


def test_study_reproducible_and_not_overwritten(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    generate(a)
    generate(b)
    assert {p.name: p.read_bytes() for p in a.iterdir()} == {
        p.name: p.read_bytes() for p in b.iterdir()
    }
    with pytest.raises(AnimationError):
        generate(a)
    for name, count in (("walk", 8), ("skeleton", 8), ("travel", 24)):
        with Image.open(a / f"{name}.gif") as gif:
            assert gif.n_frames == count
            for i in range(count):
                gif.seek(i)
                assert gif.info["duration"] == 120


def test_declarative_dragon_matches_initial_study():
    path = Path(__file__).parents[1] / "mascots/dragon/mannequin.yaml"
    rig = load_rig(path)
    assert rig == Rig()
    for i in range(8):
        assert draw_pose(pose(i, rig), rig).tobytes() == draw_pose(pose(i)).tobytes()


@pytest.mark.parametrize("field,value", [
    ("thigh", 2), ("forearm", 0), ("travel_per_frame", 2),
    ("foot_x", [6, 2, 0, -3, -6, -4, 0, 5]),
    ("foot_lift", [0, 0, 0, 1, 2, 6, 8, 5]),
    ("bob", [0]), ("hip_x", 105), ("hip_y", True),
    ("head", [0, 0, -5, -5]), ("arm_swing", float("nan")),
    ("duration_ms", 125), ("ground", 111), ("hip_x", 10**400),
])
def test_invalid_declarative_rig_rejected(tmp_path, field, value):
    data = asdict(Rig())
    data[field] = value
    path = tmp_path / "rig.yaml"
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(AnimationError):
        load_rig(path)


@pytest.mark.parametrize("text", ["hip_x: 56\nhip_x: 57\n", "typo: 12\n", "[]\n"])
def test_malformed_declarative_rig_rejected(tmp_path, text):
    path = tmp_path / "rig.yaml"
    path.write_text(text)
    with pytest.raises(AnimationError):
        load_rig(path)


def test_hip_translation_moves_whole_mannequin(tmp_path):
    data = asdict(Rig())
    data["hip_x"] += 2
    path = tmp_path / "rig.yaml"
    path.write_text(yaml.safe_dump(data))
    rig = load_rig(path)
    for i in range(8):
        before, after = pose(i), pose(i, rig)
        for collection in ("arms", "legs"):
            for side, parts in before[collection].items():
                for joint, position in parts.items():
                    if joint != "support":
                        assert after[collection][side][joint] == pytest.approx(
                            (position[0] + 2, position[1])
                        )


def test_user_approved_motion_is_frozen_and_reproducible(tmp_path):
    root = Path(__file__).parents[1] / "mascots/dragon"
    approval = json.loads((root / "MOTION_APPROVAL.json").read_text())
    assert approval["status"] == "approved_motion_only"
    assert approval["evidence"] == "marche parfaite"
    for name, digest in approval["files_sha256"].items():
        assert sha256((root / name).read_bytes()).hexdigest() == digest
    target = tmp_path / "regenerated"
    generate(target, load_rig(root / "mannequin.yaml"))
    for original in (root / "motion-reference").iterdir():
        assert (target / original.name).read_bytes() == original.read_bytes()
