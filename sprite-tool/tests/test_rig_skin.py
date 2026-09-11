import json
from pathlib import Path

from PIL import Image
from sprite_animator.mannequin import pose
from sprite_animator.pipeline import generate
from sprite_animator.skin import load_skin, prepare, render_pose
from sprite_animator.storage import inventory, verify_bundle

CONFIG = Path(__file__).parents[1] / "mascots/dragon/skin.json"


def test_skin_follows_approved_joints_and_claws_belong_to_feet():
    spec, rig, parts, palette, _ = load_skin(CONFIG)
    reference = json.loads((CONFIG.parent / "motion-reference/motion.json").read_text())
    for i in range(8):
        data = pose(i, rig)
        assert json.loads(json.dumps(data)) == reference["poses"][i]
        frame, layers = render_pose(data, rig, parts, spec["source_hip"], layers=True)
        assert frame.getchannel("A").getbbox()[3] == 105
        assert all(p[3] in (0, 255) and (not p[3] or p[:3] in palette)
                   for p in frame.get_flattened_data())
        for side in ("near", "far"):
            x, y = data["legs"][side]["ankle"]
            leg = layers[f"{side}_legs"]
            assert leg.getpixel((x+2, y+rig.foot_height)) == (255, 240, 128, 255)
            assert leg.getpixel((x+5, y+rig.foot_height)) == (255, 240, 128, 255)
            if data["legs"][side]["support"]:
                assert leg.getchannel("A").getbbox()[3] == rig.ground+1
        # Head detail is a fixed prepared bitmap, translated only with the hip bob.
        expected = Image.new("RGBA", (112, 112))
        expected.alpha_composite(parts["head"], (rig.hip_x-spec["source_hip"][0],
                                                rig.hip_y-spec["source_hip"][1]+data["bob"]))
        assert layers["head"].tobytes() == expected.tobytes()


def test_skin_pipeline_reproducible_and_unapproved(tmp_path):
    before = inventory(CONFIG.parent)
    a, b = tmp_path / "a", tmp_path / "b"
    prepare(CONFIG, a)
    prepare(CONFIG, b)
    assert inventory(a) == inventory(b)
    result = generate(a / "mascot.yaml", tmp_path)
    manifest = verify_bundle(result)
    assert manifest["frame_count"] == 8
    assert len(list((result / "left").glob("frame_*.png"))) == 8
    assert not (tmp_path / "approved").exists()
    assert inventory(CONFIG.parent) == before


def test_tail_mask_excludes_original_rear_leg_without_removing_outline():
    _, _, parts, _, _ = load_skin(CONFIG)
    tail = parts["tail"]
    # V3's original rear leg lay immediately outside the dark tail contour.
    # Its eleven brown pixels must not travel with the static tail component.
    remnants = [(49, 81), (50, 81), (48, 82), (49, 82), (47, 83), (48, 83),
                (46, 84), (47, 84), (45, 85), (46, 85), (45, 86)]
    for point in remnants:
        assert tail.getpixel(point) == (0, 0, 0, 0)
    contour = [(48, 81), (47, 82), (46, 83), (45, 84), (44, 85), (44, 86), (44, 87)]
    for point in contour:
        assert tail.getpixel(point) == (16, 0, 32, 255)
