"""Read-only preflight against the real production asset validator and codec.

No approvals, BMP exports, generated headers or firmware writes are performed.
Codec compatibility and production acceptance are deliberately separate results.
"""

import argparse
import json
import runpy
from pathlib import Path

from PIL import Image

from .storage import verify_bundle


def check(candidate, repo):
    candidate, repo = Path(candidate), Path(repo)
    manifest = verify_bundle(candidate)
    codec = runpy.run_path(str(repo / "tools/generate_tft_assets.py"))
    key = codec["TRANSPARENT_RGB"]
    catalog = {}
    for source in sorted((repo / "assets/tft").glob("*.bmp")):
        width, height, pixels = codec["read_color_bmp"](source)
        pixels, _ = codec["normalize_transparent_matte"](width, height, pixels)
        catalog[codec["asset_name"](source)] = (width, height, pixels)
    original_count = len(catalog)
    measured = []
    for direction in ("right", "left"):
        for index in range(manifest["frame_count"]):
            with Image.open(candidate / direction / f"frame_{index:02}.png") as image:
                pixels = [p[:3] if p[3] else key for p in image.get_flattened_data()]
                width, height = image.size
            words = [codec["rgb565"](*rgb) for rgb in pixels]
            compressed = codec["compress_pixels"](words)
            if codec["decompress_pixels"](compressed, width*height) != words:
                raise ValueError("Production codec roundtrip mismatch")
            name = f"{manifest['mascot']}_walk_{direction}_{index+1:02}"
            catalog[name] = (width, height, pixels)
            measured.append({"name": name, "visible_pixels": sum(p != key for p in pixels),
                             "rle_bytes": len(compressed)})
    error = None
    try:
        codec["validate_asset_scale"](catalog)
    except ValueError as exc:
        error = str(exc)
    return {
        "status": "read_only_preflight_not_approval",
        "codec_roundtrip": "passed",
        "production_asset_validation": "blocked" if error else "passed",
        "production_validation_error": error,
        "production_visible_pixel_range": list(codec["DRAGON_VISIBLE_PIXEL_RANGE"]),
        "approved_rigged_walk_visible_pixel_range": list(codec["RIGGED_WALK_VISIBLE_PIXEL_RANGE"]),
        "current_catalog_count": original_count,
        "proposed_catalog_count": len(catalog),
        "candidate_frames": measured,
        "requirements_not_verified_by_this_check": ["Human approval of the complete skinned cycle",
                            "Firmware playback timing, travel and catalog integration",
                            "Real ST7789 verification"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    result = check(args.candidate, args.repo)
    print(json.dumps(result, indent=2))
    if result["production_asset_validation"] == "blocked":
        parser.exit(2)


if __name__ == "__main__":
    main()
