import copy

import pytest
import yaml
from PIL import Image
from sprite_animator.config import load_model
from sprite_animator.errors import AnimationError
from sprite_animator.renderer import render


def change(config, edit):
    data = yaml.safe_load(config.read_text())
    edit(data)
    config.write_text(yaml.safe_dump(data))


@pytest.mark.parametrize(
    "edit, message",
    [
        (lambda d: d.update(surprise=1), "Additional properties"),
        (lambda d: d["canvas"].update(width=32.5), "integer"),
        (lambda d: d["canvas"].update(ground_y=32), "outside"),
        (lambda d: d["layers"].append(copy.deepcopy(d["layers"][0])), "Duplicate layer"),
        (lambda d: d["layers"][0].update(parent="absent"), "unknown parent"),
        (lambda d: d["layers"][0].update(parent="head"), "Parent cycle"),
        (lambda d: d["layers"][0].update(track="absent"), "unknown track"),
        (lambda d: d["layers"][2]["poses"].pop("forward"), "missing pose"),
        (lambda d: d["layers"][0].update(source="absent.png"), "Cannot load asset"),
        (lambda d: d["layers"][0].update(anchor=[-40, 0]), "outside canvas"),
        (lambda d: d["canvas"].update(ground_y=30), "ground"),
        (lambda d: d.update(overrides={"walk": {"frame_0": {"absent": {}}}}), "unknown layer"),
        (lambda d: d.update(overrides={"walk": {"frame_6": {}}}), "exceeds frame count"),
        (lambda d: d["layers"][0].update(anchor=[True, 0]), "integer"),
    ],
)
def test_invalid_config(project, edit, message):
    _, config = project
    change(config, edit)
    with pytest.raises(AnimationError, match=message):
        render(load_model(config))


def test_duplicate_yaml(project):
    _, config = project
    config.write_text(config.read_text() + "\nid: duplicate\n")
    with pytest.raises(AnimationError, match="Duplicate YAML key"):
        load_model(config)


@pytest.mark.parametrize(
    "pixel, message", [((99, 99, 99, 255), "outside palette"), ((24, 34, 56, 128), "partial alpha")]
)
def test_invalid_pixel(project, pixel, message):
    _, config = project
    path = config.parent / "head.png"
    with Image.open(path) as source:
        im = source.convert("RGBA")
    im.putpixel((1, 1), pixel)
    im.save(path)
    with pytest.raises(AnimationError, match=message):
        load_model(config)


def test_stable_z_order_independent_of_declaration(project):
    _, config = project
    baseline = render(load_model(config))["right"]
    change(config, lambda d: d["layers"].reverse())
    assert [im.tobytes() for im in render(load_model(config))["right"]] == [
        im.tobytes() for im in baseline
    ]


def test_parent_anchors_poses_overrides_and_mirror(project):
    _, config = project
    model = load_model(config)
    frames = render(model)
    # Body at (9,14); head anchor relative to body (8,-4).
    assert frames["right"][0].getpixel((18, 10)) == (24, 34, 56, 255)
    assert frames["right"][0].getpixel((20, 11)) == (248, 208, 48, 255)
    # Near leg's forward foot, then backward foot three poses later.
    assert frames["right"][0].getpixel((21, 27))[3] == 255
    assert frames["right"][3].getpixel((15, 27))[3] == 255
    assert frames["right"][3].getpixel((21, 27))[3] == 0
    for right, left in zip(frames["right"], frames["left"], strict=True):
        assert left.tobytes() == right.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes()
    change(
        config,
        lambda d: d.update(
            overrides={
                "walk": {"frame_0": {"body": {"offset": [1, 0]}, "near_leg": {"pose": "backward"}}}
            }
        ),
    )
    updated = render(load_model(config))["right"]
    assert updated[0].getpixel((18, 10))[3] == 0
    assert updated[0].getpixel((19, 10))[3] == 255
    assert updated[0].getpixel((21, 27))[3] == 0
    assert updated[1].tobytes() == frames["right"][1].tobytes()


def test_binary_mask_and_patch(project):
    _, config = project
    mask = Image.new("RGB", (6, 5), "white")
    mask.putpixel((3, 2), (0, 0, 0))
    mask.save(config.parent / "mask.png")
    change(config, lambda d: d["layers"][1].update(mask="mask.png"))
    frames = render(load_model(config))["right"]
    assert frames[0].getpixel((20, 12))[3] == 0
    # A patch is just a final layer with a high z-index and one-pixel PNG.
    Image.new("RGBA", (1, 1), (224, 80, 64, 255)).save(config.parent / "patch.png")
    change(
        config,
        lambda d: d["layers"].append(
            {"id": "patch", "source": "patch.png", "anchor": [20, 12], "z_index": 100}
        ),
    )
    assert render(load_model(config))["right"][0].getpixel((20, 12)) == (224, 80, 64, 255)


def test_bad_profile(project):
    _, config = project
    path = config.parent / "profile.yaml"
    data = yaml.safe_load(path.read_text())
    data["tracks"]["near_leg"].pop()
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(AnimationError, match="too short"):
        load_model(config)
