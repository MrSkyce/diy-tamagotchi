import json
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image, ImageOps

from sprite_animator.mannequin import DEFAULT_RIG, pose, validate_rig
from sprite_animator.pipeline import generate
from sprite_animator.storage import inventory, verify_bundle
from sprite_animator.variants import build, prepare_parts, render

ROOT = Path(__file__).parents[1]
SPECIES = ("blue_cat", "red_dog", "green_mouse", "yellow_bird", "purple_salamander")


@pytest.mark.parametrize("version", (1, 2, 3, 4))
@pytest.mark.parametrize("species", SPECIES)
def test_species_motion_palette_parts_and_no_borrowed_claws(species, version):
    config = ROOT / "mascots" / species / f"variant-skin-v{version}.json"
    spec = json.loads(config.read_text())
    rig = replace(DEFAULT_RIG, **spec["rig_overrides"])
    validate_rig(rig)
    parts, palette = prepare_parts(config.parent / spec["source"], spec)
    outputs = []
    for i in range(8):
        data = pose(i, rig)
        frame, layers = render(data, rig, parts, spec, layers=True)
        outputs.append(frame.tobytes())
        assert frame.size == (112, 112)
        assert frame.getchannel("A").getbbox()[3] == 105
        assert all(p[3] in (0, 255) and (not p[3] or p[:3] in palette)
                   for p in frame.get_flattened_data())
        for name, part in parts.items():
            expected = Image.new("RGBA", (112, 112))
            expected.alpha_composite(part, (rig.hip_x-spec["source_hip"][0],
                                            rig.hip_y-spec["source_hip"][1]+data["bob"]))
            assert layers[name].tobytes() == expected.tobytes()
        for side in ("near", "far"):
            if data["legs"][side]["support"]:
                assert layers[f"{side}_legs"].getchannel("A").getbbox()[3] == 105
            for collection in ("legs", "arms"):
                allowed = {tuple(bytes.fromhex(spec["colors"][c][1:]))
                           for c in ("near", "far", "outline", "foot")}
                assert all(not p[3] or p[:3] in allowed
                           for p in layers[f"{side}_{collection}"].get_flattened_data())
        if species == "yellow_bird":
            assert layers["near_arms"].getbbox() is None
            assert layers["far_arms"].getbbox() is None
    assert len(set(outputs)) == 8
    # A planted ankle stays at the same world coordinate over support phase.
    assert len({pose(i, rig)["legs"]["near"]["ankle"][0]+i*rig.travel_per_frame
                for i in range(4)}) == 1


@pytest.mark.parametrize("version", (1, 2, 3, 4))
@pytest.mark.parametrize("species", SPECIES)
def test_variant_compiles_reproducibly_without_approval_or_source_mutation(tmp_path, species, version):
    config = ROOT / "mascots" / species / f"variant-skin-v{version}.json"
    before = inventory(config.parent)
    first, second = tmp_path / "first", tmp_path / "second"
    build(config, first)
    build(config, second)
    assert inventory(first) == inventory(second)
    result = generate(first / "mascot.yaml", tmp_path)
    assert verify_bundle(result)["frame_count"] == 8
    for i in range(8):
        with Image.open(result / "right" / f"frame_{i:02}.png") as right:
            with Image.open(result / "left" / f"frame_{i:02}.png") as left:
                assert ImageOps.mirror(right).tobytes() == left.tobytes()
    assert not (tmp_path / "approved").exists()
    assert not (tmp_path / "firmware-export").exists()
    assert inventory(config.parent) == before


@pytest.mark.parametrize("version", (2, 3))
@pytest.mark.parametrize("species", SPECIES)
def test_refined_feet_preserve_motion_and_every_other_pixel(species, version):
    folder = ROOT / "mascots" / species
    old = json.loads((folder / "variant-skin-v1.json").read_text())
    new = json.loads((folder / f"variant-skin-v{version}.json").read_text())
    small = json.loads((folder / "variant-skin-v2.json").read_text())
    assert {k: v for k, v in new.items() if k not in ("id", "foot_style")} == {
        k: v for k, v in old.items() if k != "id"}
    rig = replace(DEFAULT_RIG, **old["rig_overrides"])
    parts, _ = prepare_parts(folder / old["source"], old)
    recorded = json.loads((ROOT / "prepared-skins" / f"{species}-v1" / "preparation.json").read_text())
    for i in range(8):
        data = pose(i, rig)
        assert json.loads(json.dumps(data)) == recorded["poses"][i]
        before, old_layers = render(data, rig, parts, old, layers=True)
        after, new_layers = render(data, rig, parts, new, layers=True)
        _, small_layers = render(data, rig, parts, small, layers=True)
        with Image.open(ROOT / "generated" / f"{species}_rigged" / "walk" / "right" / f"frame_{i:02}.png") as saved:
            assert before.tobytes() == saved.tobytes()
        zones = []
        for side in ("near", "far"):
            x, y = data["legs"][side]["ankle"]
            crop = (x-6, y-(4 if version == 3 else 2), x+10, y+4)
            zones.append(crop)
            old_area = sum(p > 0 for p in old_layers[f"{side}_legs"].getchannel("A").crop(crop).get_flattened_data())
            new_area = sum(p > 0 for p in new_layers[f"{side}_legs"].getchannel("A").crop(crop).get_flattened_data())
            if version == 2:
                assert new_area < old_area
            else:
                # Compare to the rejected small paws, not a crop including
                # V1's thick shin during deeply bent airborne poses.
                small_area = sum(p > 0 for p in small_layers[f"{side}_legs"].getchannel("A").crop(crop).get_flattened_data())
                assert new_area > small_area
        for name in old_layers:
            if name not in ("near_legs", "far_legs"):
                assert old_layers[name].tobytes() == new_layers[name].tobytes()
        assert before.tobytes() != after.tobytes()
        for y in range(112):
            for x in range(112):
                if not any(x0 <= x < x1 and y0 <= y < y1 for x0, y0, x1, y1 in zones):
                    assert before.getpixel((x, y)) == after.getpixel((x, y))


@pytest.mark.parametrize("species", SPECIES)
def test_cartoon_ankle_continuity_on_all_eight_poses(species):
    folder = ROOT / "mascots" / species
    old = json.loads((folder / "variant-skin-v3.json").read_text())
    new = json.loads((folder / "variant-skin-v4.json").read_text())
    assert {k: v for k, v in new.items() if k not in ("id", "continuous_ankle")} == {
        k: v for k, v in old.items() if k != "id"}
    rig = replace(DEFAULT_RIG, **old["rig_overrides"])
    parts, _ = prepare_parts(folder / old["source"], old)
    for i in range(8):
        data = pose(i, rig)
        _, before = render(data, rig, parts, old, layers=True)
        _, after = render(data, rig, parts, new, layers=True)
        for name in before:
            if name not in ("near_legs", "far_legs"):
                assert before[name].tobytes() == after[name].tobytes()
        for side in ("near", "far"):
            leg = after[f"{side}_legs"]
            previous = before[f"{side}_legs"]
            ankle = data["legs"][side]["ankle"]
            x, y = ankle
            start = tuple(round(c) for c in data["legs"][side]["knee"])
            color = leg.getpixel(start)
            assert color[3] == 255
            # Colored connection, not merely two outlines touching each other.
            seen, pending = {start}, [start]
            while pending:
                px, py = pending.pop()
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        point = (px+dx, py+dy)
                        if (point not in seen and 0 <= point[0] < 112 and 0 <= point[1] < 112
                                and leg.getpixel(point) == color):
                            seen.add(point)
                            pending.append(point)
            assert ankle in seen, (species, i, side, "detached ankle")
            assert (x+4, y+1) in seen, (species, i, side, "detached cartoon foot")
            # All changes confined to the join, including a byte-identical sole.
            for py in range(112):
                for px in range(112):
                    if not (x-6 <= px <= x+9 and y-4 <= py <= y):
                        assert leg.getpixel((px, py)) == previous.getpixel((px, py))
