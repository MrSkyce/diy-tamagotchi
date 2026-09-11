from pathlib import Path

from PIL import Image

from ..errors import AnimationError
from ..storage import (
    inventory,
    output_path,
    read_json,
    safe_member,
    transaction,
    verify_bundle,
    write_json,
)
from ..validators import sha256
from .rgb565 import cpp_header, encode, rgb565


def export(
    root: Path,
    mascot: str,
    *,
    fmt="rgb565",
    byte_order="little",
    transparency="key",
    key=(255, 0, 255),
    force=False,
):
    source = output_path(root, "approved", mascot)
    manifest = verify_bundle(source)
    approval = read_json(safe_member(source, "approval.json"))
    if (
        not isinstance(approval, dict)
        or approval.get("schema_version") != 1
        or not isinstance(approval.get("reviewed_by"), str)
        or not approval["reviewed_by"].strip()
        or approval.get("manifest_sha256") != sha256((source / "manifest.json").read_bytes())
        or manifest["mascot"] != mascot
    ):
        raise AnimationError("Approval does not match the validated animation")
    if fmt not in ("rgb565", "cpp", "bmp"):
        raise AnimationError(f"Unsupported export format: {fmt}")
    if fmt == "bmp" and (
        transparency != "key"
        or key != (255, 0, 255)
        or (manifest["width"], manifest["height"]) != (112, 112)
    ):
        raise AnimationError("Production BMP export requires 112×112 and magenta key transparency")
    frames = {}
    for direction in ("right", "left"):
        frames[direction] = []
        for index in range(manifest["frame_count"]):
            with Image.open(source / direction / f"frame_{index:02}.png") as original:
                im = original.convert("RGBA")
            if im.size != (manifest["width"], manifest["height"]):
                raise AnimationError("Approved frame dimensions differ from manifest")
            frames[direction].append(im)
    target = output_path(root, "firmware-export", mascot)
    with transaction(target, force) as temporary:
        for direction, images in frames.items():
            pixels = bytearray()
            masks = bytearray()
            for index, im in enumerate(images):
                encoded, mask = encode(im, byte_order, transparency, key)
                pixels.extend(encoded)
                if mask is not None:
                    masks.extend(mask)
                if fmt == "bmp":
                    bmp = Image.new("RGB", im.size, key)
                    bmp.paste(im, mask=im.getchannel("A"))
                    bmp.save(temporary / f"{mascot}_walk_{direction}_{index + 1:02}.bmp")
            if fmt == "rgb565":
                (temporary / f"{direction}.rgb565").write_bytes(pixels)
                if transparency == "mask":
                    (temporary / f"{direction}.mask").write_bytes(masks)
            elif fmt == "cpp":
                symbol = f"{mascot}_walk_{direction}"
                (temporary / f"{direction}.h").write_text(
                    cpp_header(
                        symbol,
                        bytes(pixels),
                        bytes(masks) if transparency == "mask" else None,
                        manifest["width"],
                        manifest["height"],
                        manifest["duration_ms"],
                        byte_order,
                        rgb565(*key),
                        frame_count=manifest["frame_count"],
                    ),
                    encoding="utf-8",
                )
        write_json(
            temporary / "metadata.json",
            {
                "schema_version": 1,
                "mascot": mascot,
                "animation": "walk",
                "format": fmt,
                "width": manifest["width"],
                "height": manifest["height"],
                "frame_count": manifest["frame_count"],
                "duration_ms": manifest["duration_ms"],
                "byte_order": byte_order,
                "transparency": transparency,
                "key_rgb": list(key),
                "key_rgb565": rgb565(*key),
                "directions": ["right", "left"],
                "pixel_layout": "frame-major, row-major",
                "mask_layout": "MSB first, each frame padded to a byte boundary",
                "approved_manifest_sha256": approval["manifest_sha256"],
                "files": inventory(temporary),
            },
        )
    return target
