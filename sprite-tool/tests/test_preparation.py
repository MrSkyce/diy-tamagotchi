import json
from pathlib import Path

import pytest
import yaml
from PIL import Image
from sprite_animator.errors import AnimationError
from sprite_animator.preparation import prepare_layers
from sprite_animator.storage import inventory
from sprite_animator.validators import sha256


def test_dragon_layers_recompose_exactly_and_are_disjoint(tmp_path):
    tool = Path(__file__).resolve().parents[1]
    spec = tool / "mascots/dragon/preparation.yaml"
    target = prepare_layers(spec, tmp_path)
    report = json.loads((target / "preparation.json").read_text())
    assert report["exact_recomposition"]
    assert len(report["layers_in_sheet_order"]) == 8
    with Image.open(tool / "references/dragon/walk_right_01.png") as original:
        source = original.convert("RGBA")
    for point in report["explicitly_cleared_pixels"]:
        source.putpixel(tuple(point), (0, 0, 0, 0))
    combined = Image.new("RGBA", source.size)
    used = set()
    for name in report["layers_in_sheet_order"]:
        with Image.open(target / f"{name}.png") as layer:
            indices = {i for i, p in enumerate(layer.get_flattened_data()) if p[3]}
            assert not used & indices
            used |= indices
            combined.alpha_composite(layer)
    assert combined.tobytes() == source.tobytes()
    assert inventory(prepare_layers(spec, tmp_path / "second")) == inventory(target)
    with pytest.raises(AnimationError, match="already exists"):
        prepare_layers(spec, tmp_path)


def test_preparation_rejects_changed_reference(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGBA", (4, 4), "red").save(source)
    spec = {
        "schema_version": 1,
        "id": "test",
        "source": "source.png",
        "source_sha256": sha256(source.read_bytes()),
        "remainder": "body",
        "parts": [{"id": "head", "polygon": [[0, 0], [1, 0], [1, 1], [0, 1]]}],
    }
    path = tmp_path / "preparation.yaml"
    path.write_text(yaml.safe_dump(spec))
    Image.new("RGBA", (4, 4), "blue").save(source)
    with pytest.raises(AnimationError, match="SHA-256"):
        prepare_layers(path, tmp_path)
