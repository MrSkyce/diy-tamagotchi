from PIL import Image

from .errors import AnimationError
from .model import Model, Step


def render(model: Model) -> dict[str, list[Image.Image]]:
    """Resolve anchor hierarchy before painting in stable (z_index, id) order.

    Anchor is parent-relative (canvas-relative for roots); pivot is source-local.
    Track offsets are scaled then added, overrides add unscaled offsets.
    Parents transmit translation only. Mirroring is about the source rectangle.
    """
    by_id = {layer.id: layer for layer in model.layers}
    frames = []
    for index in range(model.frame_count):
        canvas = Image.new("RGBA", (model.width, model.height))
        anchors = {}
        poses = {}

        def resolve(name, index=index, anchors=anchors, poses=poses):
            if name in anchors:
                return anchors[name]
            layer = by_id[name]
            step = model.tracks[layer.track][(index + layer.phase) % model.frame_count] if layer.track else Step()
            override = model.overrides.get(index, {}).get(name, Step())
            parent = resolve(layer.parent) if layer.parent else (0, 0)
            anchors[name] = tuple(
                parent[axis]
                + layer.anchor[axis]
                + step.offset[axis] * layer.offset_scale[axis]
                + override.offset[axis]
                for axis in (0, 1)
            )
            poses[name] = override.pose or step.pose or "default"
            return anchors[name]

        for layer in sorted(model.layers, key=lambda item: (item.z_index, item.id)):
            anchor = resolve(layer.id)
            image = layer.images[poses[layer.id]]
            pivot_x = image.width - 1 - layer.pivot[0] if layer.mirror else layer.pivot[0]
            x, y = anchor[0] - pivot_x, anchor[1] - layer.pivot[1]
            bounds = image.getchannel("A").getbbox()
            if bounds and (
                x + bounds[0] < 0
                or y + bounds[1] < 0
                or x + bounds[2] > model.width
                or y + bounds[3] > model.height
            ):
                raise AnimationError(f"{layer.id}, frame_{index}: opaque pixels outside canvas")
            canvas.alpha_composite(image, (x, y))
        bounds = canvas.getchannel("A").getbbox()
        if bounds is None:
            raise AnimationError(f"frame_{index}: empty sprite")
        ground = bounds[3] - 1
        if abs(ground - model.ground_y) > model.ground_tolerance:
            raise AnimationError(
                f"frame_{index}: ground {ground}, expected {model.ground_y} "
                f"±{model.ground_tolerance}"
            )
        frames.append(canvas)
    return {
        "right": frames,
        "left": [im.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for im in frames],
    }
