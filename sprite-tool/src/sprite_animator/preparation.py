from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from .config import read_config
from .errors import AnimationError
from .storage import inventory, transaction, write_json
from .validators import sha256


def prepare_layers(spec: Path, root: Path, force=False):
    """Execute manually specified pixel selections, not inferred segmentation.

    Parts claim visible pixels in declaration order; the remainder receives
    everything unclaimed. No resampling, inpainting, deformation or recoloring.
    Only explicitly listed clear_pixels are removed on the working copy.
    That cleaned pose must recompose byte-for-byte before publication.
    """
    spec = spec.resolve()
    data = read_config(spec, "preparation")
    source = (spec.parent / data["source"]).resolve()
    if sha256(source.read_bytes()) != data["source_sha256"]:
        raise AnimationError("Preparation reference SHA-256 differs from the reviewed source")
    with Image.open(source) as original:
        if original.format != "PNG" or original.mode != "RGBA" or max(original.size) > 512:
            raise AnimationError("Preparation requires an RGBA PNG no larger than 512×512")
        image = original.copy()
    if any(
        p[3] not in (0, 255) or (p[3] == 0 and p[:3] != (0, 0, 0))
        for p in image.get_flattened_data()
    ):
        raise AnimationError("Preparation source must have canonical binary alpha")
    for x, y in data.get("clear_pixels", []):
        if x >= image.width or y >= image.height:
            raise AnimationError("Clear pixel is outside source canvas")
        image.putpixel((x, y), (0, 0, 0, 0))
    ids = [part["id"] for part in data["parts"]] + [data["remainder"]]
    if len(set(ids)) != len(ids):
        raise AnimationError("Duplicate preparation layer identifiers")
    remaining = image.getchannel("A")
    layers = []
    masks = []
    for part in data["parts"]:
        if any(x >= image.width or y >= image.height for x, y in part["polygon"]):
            raise AnimationError(f"{part['id']}: polygon outside source canvas")
        mask = Image.new("L", image.size)
        ImageDraw.Draw(mask).polygon([tuple(p) for p in part["polygon"]], fill=255)
        selected = ImageChops.multiply(mask, remaining)
        if selected.getbbox() is None:
            raise AnimationError(f"{part['id']}: selection contains no unclaimed visible pixels")
        remaining = ImageChops.subtract(remaining, selected)
        masks.append((part["id"], selected))
    if remaining.getbbox() is None:
        raise AnimationError("Remainder layer is empty")
    masks.append((data["remainder"], remaining))
    recomposed = Image.new("RGBA", image.size)
    for name, mask in masks:
        layer = Image.new("RGBA", image.size)
        layer.paste(image, mask=mask)
        recomposed.alpha_composite(layer)
        layers.append((name, layer))
    if recomposed.tobytes() != image.tobytes():
        raise AnimationError("Extracted layers do not reproduce every reference pixel")
    target = root.resolve() / "prepared-layers" / data["id"]
    with transaction(target, force, [spec, source]) as temporary:
        for name, layer in layers:
            layer.save(temporary / f"{name}.png", optimize=False, compress_level=9)
        recomposed.save(temporary / "recomposed.png", optimize=False, compress_level=9)
        sheet = Image.new("RGBA", (image.width * len(layers), image.height))
        for index, (_, layer) in enumerate(layers):
            sheet.paste(layer, (index * image.width, 0))
        sheet.save(temporary / "layers.png", optimize=False, compress_level=9)
        write_json(
            temporary / "preparation.json",
            {
                "schema_version": 1,
                "mascot": data["id"],
                "status": "initial_layers_review_pending",
                "source_sha256": data["source_sha256"],
                "spec_sha256": sha256(spec.read_bytes()),
                "recomposition_pixel_sha256": sha256(recomposed.tobytes()),
                "exact_recomposition": True,
                "explicitly_cleared_pixels": data.get("clear_pixels", []),
                "layers_in_sheet_order": [name for name, _ in layers],
                "remaining_work": [
                    "review anatomical cuts",
                    "draw occluded surfaces",
                    "draw alternative poses",
                    "review animated movement",
                ],
                "files": inventory(temporary),
            },
        )
    return target
