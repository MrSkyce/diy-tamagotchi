"""Real reference format checks; these are NOT six approved walk animations."""

import hashlib
import json
import runpy
from pathlib import Path

import pytest
import yaml
from PIL import Image
from sprite_animator.exporters.bundle import export
from sprite_animator.pipeline import approve, generate, validate

REPO = Path(__file__).resolve().parents[2]
APPROVAL = json.loads((REPO / "design/mascots-v1/APPROVAL.json").read_text())
REFERENCES = [("dragon", "assets/tft/dragon_idle1.bmp", None)] + [
    (model["id"], model["file"], model["sha256"]) for model in APPROVAL["models"]
]


@pytest.mark.parametrize("name,relative,expected_sha", REFERENCES)
def test_real_reference_palette_is_supported(tmp_path, name, relative, expected_sha):
    source = REPO / relative
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    if expected_sha:
        assert before == expected_sha
    with Image.open(source) as bmp:
        image = bmp.convert("RGBA")
    pixels = [p if p[:3] != (255, 0, 255) else (0, 0, 0, 0) for p in image.get_flattened_data()]
    image.putdata(pixels)
    image.save(tmp_path / "reference.png")
    palette = sorted({p[:3] for p in pixels if p[3]})
    profile = {
        "schema_version": 1,
        "id": "static_reference_check",
        "animation": "walk",
        "frames": 6,
        "duration_ms": 120,
        "tracks": {"static": [{} for _ in range(6)]},
    }
    (tmp_path / "profile.yaml").write_text(yaml.safe_dump(profile))
    config = {
        "schema_version": 1,
        "id": name,
        "canvas": {"width": 112, "height": 112, "ground_y": image.getchannel("A").getbbox()[3] - 1},
        "palette": ["#%02X%02X%02X" % rgb for rgb in palette],
        "animation_profiles": {"walk": "profile.yaml"},
        "layers": [{"id": "reference", "source": "reference.png", "anchor": [0, 0], "z_index": 0}],
    }
    path = tmp_path / "mascot.yaml"
    path.write_text(yaml.safe_dump(config))
    _, frames, report = validate(path)
    assert frames["right"][0].tobytes() == image.tobytes()
    assert report["unique_poses"] == 1  # Format smoke test, explicitly not movement.
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_bmp_export_against_existing_firmware_codec(project):
    root, config = project
    data = yaml.safe_load(config.read_text())
    data["canvas"].update(width=112, height=112)
    config.write_text(yaml.safe_dump(data))
    generate(config, root)
    approve(root, "demo_biped", "synthetic integration test")
    exported = export(root, "demo_biped", fmt="bmp")
    codec = runpy.run_path(str(REPO / "tools/generate_tft_assets.py"))
    files = sorted(exported.glob("*.bmp"))
    assert len(files) == 12
    for bmp in files:
        width, height, pixels = codec["read_color_bmp"](bmp)
        assert (width, height) == (112, 112)
        words = [codec["rgb565"](*rgb) for rgb in pixels]
        assert codec["decompress_pixels"](codec["compress_pixels"](words), 112 * 112) == words
