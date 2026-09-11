import copy
import json
from dataclasses import replace

import pytest
import yaml
from PIL import Image
from sprite_animator.config import load_model
from sprite_animator.errors import AnimationError
from sprite_animator.pipeline import approve, generate
from sprite_animator.renderer import render
from sprite_animator.storage import inventory, output_path, verify_bundle


def test_pivot_mirror_and_inherited_offset(project):
    _, config = project
    original = load_model(config)
    head = next(layer for layer in original.layers if layer.id == "head")
    # Moving the pivot and anchor by the same amount preserves every pixel.
    shifted = replace(head, anchor=(head.anchor[0] + 2, head.anchor[1] + 1), pivot=(2, 1))
    altered = replace(
        original,
        layers=tuple(shifted if layer.id == "head" else layer for layer in original.layers),
    )
    assert render(original)["right"][0].tobytes() == render(altered)["right"][0].tobytes()
    # Mirroring a layer reflects around its local pivot, independent of parent.
    data = yaml.safe_load(config.read_text())
    data["layers"][1].update(mirror=True, pivot=[2, 0], anchor=[10, -4])
    config.write_text(yaml.safe_dump(data))
    model = load_model(config)
    mirrored_head = next(layer for layer in model.layers if layer.id == "head")
    assert (
        mirrored_head.images["default"].tobytes()
        == head.images["default"].transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes()
    )
    # World anchor is 19; mirrored pivot is 3 => image starts at x=16.
    frame = render(model)["right"][0]
    assert frame.getpixel((16, 10)) == (24, 34, 56, 255)


def test_phase_and_integer_offset_scaling(project):
    _, config = project
    baseline = render(load_model(config))["right"]
    data = yaml.safe_load(config.read_text())
    data["layers"][1].update(phase=2, offset_scale=[1, 2])
    config.write_text(yaml.safe_dump(data))
    updated = render(load_model(config))["right"]
    assert baseline[0].getpixel((18, 10))[3] == 255
    assert updated[0].getpixel((18, 10))[3] == 0
    assert updated[0].getpixel((18, 12))[3] == 255


@pytest.mark.parametrize("malformation", ["partial", "gray", "dimensions"])
def test_mask_errors(project, malformation):
    _, config = project
    mask = Image.new("RGBA", (6, 5), "white")
    if malformation == "partial":
        mask.putpixel((0, 0), (255, 255, 255, 128))
    elif malformation == "gray":
        mask.putpixel((0, 0), (127, 127, 127, 255))
    else:
        mask = Image.new("RGBA", (7, 5), "white")
    mask.save(config.parent / "mask.png")
    data = yaml.safe_load(config.read_text())
    data["layers"][1]["mask"] = "mask.png"
    config.write_text(yaml.safe_dump(data))
    with pytest.raises(AnimationError):
        load_model(config)


def test_approval_force_preserves_previous_revision(project):
    root, config = project
    generate(config, root)
    target = approve(root, "demo_biped", "first fixture reviewer")
    before = inventory(target)
    approve(root, "demo_biped", "second fixture reviewer", force=True)
    previous = list(target.parent.glob(".walk.previous-*"))
    assert len(previous) == 1 and inventory(previous[0]) == before
    assert (
        json.loads((target / "approval.json").read_text())["reviewed_by"]
        == "second fixture reviewer"
    )


@pytest.mark.parametrize("value", [None, "", "../dragon", "/tmp/dragon", "dragon/walk"])
def test_invalid_output_identifier(tmp_path, value):
    with pytest.raises(AnimationError):
        output_path(tmp_path, "generated", value)


@pytest.mark.parametrize(
    "edit",
    [
        lambda d: d.update(width="112"),
        lambda d: d.update(palette=None),
        lambda d: d.update(duration_ms=0),
        lambda d: d.update(mascot=None),
        lambda d: d["files"].update({"../source.png": "abc"}),
    ],
)
def test_malformed_manifest_rejected(project, edit):
    root, config = project
    target = generate(config, root)
    path = target / "manifest.json"
    manifest = copy.deepcopy(json.loads(path.read_text()))
    edit(manifest)
    path.write_text(json.dumps(manifest))
    with pytest.raises(AnimationError):
        verify_bundle(target)
