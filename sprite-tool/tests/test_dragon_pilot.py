import runpy
from pathlib import Path

import yaml
from PIL import Image
from sprite_animator.pipeline import validate

TOOL = Path(__file__).resolve().parents[1]
REPO = TOOL.parent


def test_explicit_cleanup_matches_existing_production_renderer():
    codec = runpy.run_path(str(REPO / "tools/generate_tft_assets.py"))
    width, height, pixels = codec["read_color_bmp"](REPO / "assets/tft/dragon_walk_right_01.bmp")
    cleaned, count = codec["normalize_transparent_matte"](width, height, pixels)
    spec = yaml.safe_load((TOOL / "mascots/dragon/preparation.yaml").read_text())
    actual = [
        [i % width, i // width]
        for i, (before, after) in enumerate(zip(pixels, cleaned, strict=True))
        if before != after
    ]
    assert count == 57
    assert spec["clear_pixels"] == actual
    with Image.open(TOOL / "prepared-layers/dragon/recomposed.png") as recomposed:
        expected = [(*p, 255) if p != (255, 0, 255) else (0, 0, 0, 0) for p in cleaned]
        assert list(recomposed.get_flattened_data()) == expected


def test_real_dragon_cycle_keeps_identity_and_stance():
    model, frames, report = validate(TOOL / "mascots/dragon/mascot.yaml")
    assert len(frames["right"]) == 6 and report["unique_poses"] == 6
    assert report["errors"] == []
    assert all(len(frame["component_sizes"]) == 1 for frame in report["frames"])
    with Image.open(TOOL / "prepared-layers/dragon/recomposed.png") as original:
        identity = original.crop((0, 0, 112, 67)).tobytes()
    for frame in frames["right"]:
        assert frame.crop((0, 0, 112, 67)).tobytes() == identity
        assert frame.getchannel("A").getbbox()[3] - 1 == 104
    # A global advance of +2 px/pose cancels the support foot's local motion.
    # This proves coordinates during contact, not perceived gait quality.
    for track, start in [("near_leg", 0), ("far_leg", 3)]:
        steps = model.tracks[track]
        assert len({2 * index + steps[index].offset[0] for index in range(start, start + 3)}) == 1
        assert all(steps[index].offset[1] == 0 for index in range(start, start + 3))
    assert (
        max(f["visible_pixels"] for f in report["frames"])
        / min(f["visible_pixels"] for f in report["frames"])
        < 1.06
    )
