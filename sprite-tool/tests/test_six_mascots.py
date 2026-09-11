import json
import runpy
import shutil
from pathlib import Path

import pytest
import yaml
from PIL import Image
from sprite_animator.pipeline import generate_all, validate
from sprite_animator.storage import inventory

TOOL = Path(__file__).resolve().parents[1]
REPO = TOOL.parent
IDS = ("blue_cat", "dragon", "green_mouse", "purple_salamander", "red_dog", "yellow_bird")


@pytest.mark.parametrize("mascot", IDS)
def test_real_layers_preserve_cleaned_reference(mascot):
    spec = yaml.safe_load((TOOL / "mascots" / mascot / "preparation.yaml").read_text())
    source = (TOOL / "mascots" / mascot / spec["source"]).resolve()
    with Image.open(source) as original:
        expected = original.copy()
    for point in spec["clear_pixels"]:
        expected.putpixel(tuple(point), (0, 0, 0, 0))
    folder = TOOL / "prepared-layers" / mascot
    report = json.loads((folder / "preparation.json").read_text())
    reconstructed = Image.new("RGBA", expected.size)
    used = set()
    for name in report["layers_in_sheet_order"]:
        with Image.open(folder / f"{name}.png") as layer:
            indices = {i for i, pixel in enumerate(layer.get_flattened_data()) if pixel[3]}
            assert not used & indices
            used |= indices
            reconstructed.alpha_composite(layer)
    assert reconstructed.tobytes() == expected.tobytes()


@pytest.mark.parametrize("mascot", IDS)
def test_real_cycles_preserve_faces_and_ground(mascot):
    model, directions, report = validate(TOOL / "mascots" / mascot / "mascot.yaml")
    assert report["unique_poses"] == 6
    assert all(len(frame["component_sizes"]) == 1 for frame in report["frames"])
    with Image.open(TOOL / "prepared-layers" / mascot / "recomposed.png") as source:
        face = source.crop((0, 0, 112, 67)).tobytes()
    for frame in directions["right"]:
        assert frame.crop((0, 0, 112, 67)).tobytes() == face
        assert frame.getchannel("A").getbbox()[3] - 1 == model.ground_y
    assert (
        max(f["visible_pixels"] for f in report["frames"])
        / min(f["visible_pixels"] for f in report["frames"])
        < 1.06
    )
    # Connected components and fixed faces/ground still do not prove finished art.


def test_salamander_interior_purple_is_not_cleared():
    manifest = json.loads((REPO / "design/mascots-v1/APPROVAL.json").read_text())
    model = next(m for m in manifest["models"] if m["id"] == "purple_salamander")
    interior = model["existing_normalizer_diagnostic"]["remaining_flagged_pixels"]
    assert len(interior) == 11
    with Image.open(TOOL / "prepared-layers/purple_salamander/recomposed.png") as image:
        for pixel in interior:
            assert image.getpixel((pixel["x"], pixel["y"])) == (*pixel["rgb"], 255)


def test_all_explicit_cleanup_lists_match_production_codec():
    codec = runpy.run_path(str(REPO / "tools/generate_tft_assets.py"))
    for mascot in IDS:
        source = REPO / (
            "assets/tft/dragon_walk_right_01.bmp"
            if mascot == "dragon"
            else f"design/mascots-v1/bmp/{mascot}_idle_01_candidate.bmp"
        )
        width, height, pixels = codec["read_color_bmp"](source)
        clean, _ = codec["normalize_transparent_matte"](width, height, pixels)
        expected = [
            [i % width, i // width]
            for i, (a, b) in enumerate(zip(pixels, clean, strict=True))
            if a != b
        ]
        spec = yaml.safe_load((TOOL / "mascots" / mascot / "preparation.yaml").read_text())
        assert spec["clear_pixels"] == expected


def test_generate_all_actual_six_mascots_reproducibly(tmp_path):
    # Copy only engine inputs, never the virtualenv or candidate/approved outputs.
    for workspace in (tmp_path / "first", tmp_path / "second"):
        workspace.mkdir()
        for name in ("mascots", "profiles", "prepared-layers", "references"):
            shutil.copytree(
                TOOL / name,
                workspace / name,
                ignore=shutil.ignore_patterns(".*.previous-*", "__pycache__"),
            )
        outputs = generate_all(workspace)
        assert {folder.parent.name for folder in outputs} == set(IDS)
        assert sum(len(list(folder.glob("*/frame_*.png"))) for folder in outputs) == 72
        assert not (workspace / "approved").exists()
        assert not (workspace / "firmware-export").exists()
    assert inventory(tmp_path / "first/generated") == inventory(tmp_path / "second/generated")
