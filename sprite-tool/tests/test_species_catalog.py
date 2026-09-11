import json
import runpy
import shutil
from pathlib import Path

import pytest
from PIL import Image

from sprite_animator.storage import verify_bundle
from sprite_animator.validators import sha256

ROOT = Path(__file__).parents[2]
ASSETS = ROOT / "assets/tft"
CODEC = runpy.run_path(str(ROOT / "tools/generate_tft_assets.py"))


def test_eighty_production_frames_match_approved_pixels_and_codec():
    CODEC["verify_species_walk_approval"](ASSETS)
    approval = json.loads((ASSETS / "mascot_walks_approval.json").read_text())
    assert len(approval["files_sha256"]) == 80
    for species, record in approval["cycles"].items():
        source = ROOT / "sprite-tool/approved" / record["mascot"] / "walk"
        manifest = verify_bundle(source)
        assert manifest["frame_count"] == 8
        digest = sha256((source / "manifest.json").read_bytes())
        assert digest == record["approved_manifest_sha256"]
        assert digest == json.loads((source / "approval.json").read_text())["manifest_sha256"]
        for direction in ("left", "right"):
            for i in range(8):
                name = f"{species}_rigged_feet_v4_walk_{direction}_{i+1:02}.bmp"
                width, height, pixels = CODEC["read_color_bmp"](ASSETS / name)
                with Image.open(source / direction / f"frame_{i:02}.png") as frame:
                    expected = [p[:3] if p[3] else (255, 0, 255) for p in frame.get_flattened_data()]
                assert (width, height) == (112, 112)
                assert pixels == expected
                normalized, cleaned = CODEC["normalize_transparent_matte"](width, height, pixels)
                assert cleaned == 0 and normalized == pixels
                words = [CODEC["rgb565"](*rgb) for rgb in pixels]
                assert CODEC["decompress_pixels"](CODEC["compress_pixels"](words), 112*112) == words


def test_species_approval_rejects_tampered_bmp(tmp_path):
    shutil.copyfile(ASSETS / "mascot_walks_approval.json", tmp_path / "mascot_walks_approval.json")
    record = json.loads((tmp_path / "mascot_walks_approval.json").read_text())
    # The first member is enough: corruption must fail before any later read.
    first = next(iter(record["files_sha256"]))
    (tmp_path / first).write_bytes(b"not the approved bitmap")
    with pytest.raises(ValueError, match="differs from approved"):
        CODEC["verify_species_walk_approval"](tmp_path)


def test_catalog_requires_every_species_frame_and_fits_flash():
    paths = sorted(ASSETS.glob("*.bmp"))
    assert len(paths) == 129
    assets = {}
    for path in paths:
        w, h, pixels = CODEC["read_color_bmp"](path)
        pixels, _ = CODEC["normalize_transparent_matte"](w, h, pixels)
        assets[path.stem] = w, h, pixels
    CODEC["validate_asset_scale"](assets)
    for species in CODEC["WALK_SPECIES"]:
        missing = dict(assets)
        del missing[f"{species}_rigged_feet_v4_walk_left_08"]
        with pytest.raises(ValueError, match="missing animation"):
            CODEC["validate_asset_scale"](missing)
    image, _, _ = CODEC["build_flash_image"](paths, assets)
    assert len(image) < 8*1024*1024
