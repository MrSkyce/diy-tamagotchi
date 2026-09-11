import json
from pathlib import Path

import pytest
from PIL import Image
from sprite_animator.errors import AnimationError
from sprite_animator.references import prepare_references
from sprite_animator.validators import sha256


def test_prepare_six_models_preserves_visible_pixels_and_sources(tmp_path):
    repo = Path(__file__).resolve().parents[2]
    target = prepare_references(repo, tmp_path)
    records = json.loads((target / "references.json").read_text())["references"]
    assert len(records) == 8  # Six neutral models plus two existing dragon keyframes.
    assert len({record["mascot"] for record in records}) == 6
    for record in records:
        original = repo / record["source"]
        assert sha256(original.read_bytes()) == record["source_sha256"]
        with (
            Image.open(original) as bmp,
            Image.open(target / record["mascot"] / f"{record['pose']}.png") as png,
        ):
            for rgb, rgba in zip(
                bmp.convert("RGB").get_flattened_data(), png.get_flattened_data(), strict=True
            ):
                assert rgba == ((0, 0, 0, 0) if rgb == (255, 0, 255) else (*rgb, 255))
    with pytest.raises(AnimationError, match="already exists"):
        prepare_references(repo, tmp_path)
