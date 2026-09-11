import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from PIL import Image, ImageChops, UnidentifiedImageError

from .errors import AnimationError
from .model import Layer, Model, Step


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate keys instead of silently discarding artistic overrides."""


def _mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise AnimationError("YAML mapping keys must be strings")
        if key in result:
            raise AnimationError(f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def read_config(path: Path, kind: str) -> dict:
    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueLoader)
        schema = json.loads((Path(__file__).parent / "schemas" / f"{kind}.json").read_text())
        errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: str(e.path))
        if errors:
            error = errors[0]
            location = ".".join(map(str, error.absolute_path)) or "root"
            raise AnimationError(f"{path}: {location}: {error.message}")
        return data
    except (OSError, yaml.YAMLError, RecursionError) as error:
        raise AnimationError(f"Cannot load {path}: {error}") from error


def _step(data):
    return Step(tuple(data.get("offset", [0, 0])), data.get("pose"))


def load_model(path: Path) -> Model:
    path = path.resolve()
    data = read_config(path, "mascot")
    profile_path = (path.parent / data["animation_profiles"]["walk"]).resolve()
    profile = read_config(profile_path, "profile")
    frame_count = profile["frames"]
    if any(len(track) != frame_count for track in profile["tracks"].values()):
        raise AnimationError("Every track must match the declared frame count")
    inputs = {path, profile_path}
    canvas = data["canvas"]
    if canvas["ground_y"] >= canvas["height"]:
        raise AnimationError("canvas.ground_y is outside the canvas")
    palette = tuple(tuple(bytes.fromhex(c[1:])) for c in data["palette"])
    if len(set(palette)) != len(palette):
        raise AnimationError("Duplicate palette color (case-insensitive)")
    allowed = set(palette)

    def read_image(relative, mask=False):
        asset = (path.parent / relative).resolve()
        inputs.add(asset)
        try:
            with Image.open(asset) as original:
                if original.format != "PNG" or original.width > 512 or original.height > 512:
                    raise AnimationError(f"{asset}: expected a PNG no larger than 512×512")
                if getattr(original, "n_frames", 1) != 1:
                    raise AnimationError(f"{asset}: animated source images are not allowed")
                image = original.convert("RGBA")
        except (OSError, UnidentifiedImageError) as error:
            raise AnimationError(f"Cannot load asset {asset}: {error}") from error
        pixels = list(image.get_flattened_data())
        if any(p[3] not in (0, 255) for p in pixels):
            raise AnimationError(f"{asset}: partial alpha / antialiasing is forbidden")
        if mask:
            if any(p[3] != 255 or p[:3] not in ((0, 0, 0), (255, 255, 255)) for p in pixels):
                raise AnimationError(f"{asset}: mask must be opaque binary black/white")
            return image.convert("L")
        foreign = {p[:3] for p in pixels if p[3] and p[:3] not in allowed}
        if foreign:
            raise AnimationError(f"{asset}: colors outside palette: {sorted(foreign)[:5]}")
        # Canonicalize invisible RGB channels for byte-for-byte reproducibility.
        image.putdata([p if p[3] else (0, 0, 0, 0) for p in pixels])
        return image

    tracks = {name: tuple(_step(s) for s in steps) for name, steps in profile["tracks"].items()}
    layers = []
    ids = [layer["id"] for layer in data["layers"]]
    if len(ids) != len(set(ids)):
        raise AnimationError("Duplicate layer identifiers")
    for spec in data["layers"]:
        if spec.get("phase", 0) >= frame_count:
            raise AnimationError(f"{spec['id']}: phase exceeds frame count")
        if spec.get("track") is not None and spec["track"] not in tracks:
            raise AnimationError(f"{spec['id']}: unknown track {spec['track']}")
        if spec.get("parent") is not None and spec["parent"] not in ids:
            raise AnimationError(f"{spec['id']}: unknown parent {spec['parent']}")
        if "default" in spec.get("poses", {}):
            raise AnimationError(f"{spec['id']}: pose name 'default' is reserved for source")
        images = {"default": read_image(spec["source"])}
        images.update({name: read_image(p) for name, p in spec.get("poses", {}).items()})
        if len({im.size for im in images.values()}) != 1:
            raise AnimationError(f"{spec['id']}: source and poses must have identical dimensions")
        if "mask" in spec:
            mask = read_image(spec["mask"], mask=True)
            for im in images.values():
                if mask.size != im.size:
                    raise AnimationError(f"{spec['id']}: mask dimensions differ from source")
                im.putalpha(ImageChops.multiply(im.getchannel("A"), mask))
        if spec.get("mirror", False):
            images = {
                name: im.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for name, im in images.items()
            }
        layers.append(
            Layer(
                id=spec["id"],
                anchor=tuple(spec["anchor"]),
                pivot=tuple(spec.get("pivot", [0, 0])),
                z_index=spec["z_index"],
                parent=spec.get("parent"),
                track=spec.get("track"),
                phase=spec.get("phase", 0),
                offset_scale=tuple(spec.get("offset_scale", [1, 1])),
                mirror=spec.get("mirror", False),
                images=images,
            )
        )
    by_id = {layer.id: layer for layer in layers}
    for layer in layers:
        visited = set()
        current = layer
        while current is not None:
            if current.id in visited:
                raise AnimationError(f"Parent cycle involving {current.id}")
            visited.add(current.id)
            current = by_id.get(current.parent)
    overrides = {
        int(frame.removeprefix("frame_")): {name: _step(step) for name, step in items.items()}
        for frame, items in data.get("overrides", {}).get("walk", {}).items()
    }
    for frame, items in overrides.items():
        if frame >= frame_count:
            raise AnimationError(f"frame_{frame}: override exceeds frame count")
        for name in items:
            if name not in by_id:
                raise AnimationError(f"frame_{frame}: override references unknown layer {name}")
    for layer in layers:
        for index in range(frame_count):
            base = tracks[layer.track][(index + layer.phase) % frame_count] if layer.track else Step()
            override = overrides.get(index, {}).get(layer.id, Step())
            pose = override.pose or base.pose or "default"
            if pose not in layer.images:
                raise AnimationError(f"{layer.id}, frame_{index}: missing pose {pose}")
    return Model(
        id=data["id"],
        width=canvas["width"],
        height=canvas["height"],
        ground_y=canvas["ground_y"],
        ground_tolerance=canvas.get("ground_tolerance", 0),
        palette=palette,
        duration_ms=profile["duration_ms"],
        layers=tuple(layers),
        tracks=tracks,
        overrides=overrides,
        inputs=tuple(sorted(inputs)),
        config_path=path,
        frame_count=frame_count,
    )
