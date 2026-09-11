"""Prepare lossless RGBA working references, without inventing layers or poses."""

import json
from pathlib import Path

from PIL import Image

from .errors import AnimationError
from .storage import inventory, transaction, write_json
from .validators import sha256


def prepare_references(repo: Path, root: Path, force=False):
    repo, root = repo.resolve(), root.resolve()
    try:
        approval = json.loads((repo / "design/mascots-v1/APPROVAL.json").read_text())
        approved = approval["models"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise AnimationError(f"Cannot read approved mascot references: {error}") from error
    expected = {"blue_cat", "red_dog", "green_mouse", "yellow_bird", "purple_salamander"}
    if {entry["id"] for entry in approved} != expected or len(approved) != 5:
        raise AnimationError("Expected the five approved models alongside the production dragon")
    sources = [{"id": "dragon", "file": "assets/tft/dragon_idle1.bmp", "name": "neutral"}]
    sources.extend({**entry, "name": "neutral"} for entry in approved)
    sources.extend(
        {
            "id": "dragon",
            "file": f"assets/tft/dragon_walk_right_{index:02}.bmp",
            "name": f"walk_right_{index:02}",
        }
        for index in (1, 2)
    )
    inputs = []
    prepared = []
    for entry in sources:
        source = (repo / entry["file"]).resolve()
        if repo not in source.parents:
            raise AnimationError(f"Reference outside repository: {entry['file']}")
        inputs.append(source)
        raw = source.read_bytes()
        digest = sha256(raw)
        if entry.get("sha256", digest) != digest:
            raise AnimationError(f"Approved reference has changed: {entry['file']}")
        with Image.open(source) as image:
            if image.format != "BMP" or image.size != (112, 112):
                raise AnimationError(f"Invalid reference BMP: {entry['file']}")
            rgba = image.convert("RGBA")
        # Only exact transparency key. Every visible RGB triplet is preserved,
        # including interior purple pixels and any matte awaiting explicit cleanup.
        pixels = [p if p[:3] != (255, 0, 255) else (0, 0, 0, 0) for p in rgba.get_flattened_data()]
        rgba.putdata(pixels)
        palette = sorted({p[:3] for p in pixels if p[3]})
        prepared.append((entry, rgba, digest, palette))
    target = root / "references"
    with transaction(target, force, inputs) as temporary:
        records = []
        for entry, image, digest, palette in prepared:
            folder = temporary / entry["id"]
            folder.mkdir(exist_ok=True)
            image.save(folder / f"{entry['name']}.png", optimize=False, compress_level=9)
            record = {
                "mascot": entry["id"],
                "pose": entry["name"],
                "source": entry["file"],
                "source_sha256": digest,
                "pixel_sha256": sha256(image.tobytes()),
                "palette": ["#%02X%02X%02X" % rgb for rgb in palette],
                "width": 112,
                "height": 112,
                "ground_y": image.getchannel("A").getbbox()[3] - 1,
            }
            records.append(record)
        write_json(
            temporary / "references.json",
            {
                "schema_version": 1,
                "status": "working_references_not_animation_layers",
                "transparency": "Exact #FF00FF only; visible colors unchanged",
                "remaining_work": [
                    "explicit matte cleanup",
                    "layer preparation",
                    "alternative limb poses",
                    "animation review",
                ],
                "references": records,
                "files": inventory(temporary),
            },
        )
    return target
