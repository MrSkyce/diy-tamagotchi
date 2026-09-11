import hashlib
from collections import deque

from .model import Model


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def components(image):
    opaque = {
        (x, y) for y in range(image.height) for x in range(image.width) if image.getpixel((x, y))[3]
    }
    sizes = []
    while opaque:
        queue = deque([opaque.pop()])
        size = 0
        while queue:
            x, y = queue.popleft()
            size += 1
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
                point = (x + dx, y + dy)
                if point in opaque:
                    opaque.remove(point)
                    queue.append(point)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def report(model: Model, directions) -> dict:
    warnings = ["Human review required: foot contact, limb connections and loop readability."]
    frames = []
    right = directions["right"]
    for index, image in enumerate(right):
        sizes = components(image)
        if len(sizes) > 1:
            warnings.append(
                f"frame_{index}: {len(sizes)} opaque components; inspect disconnected parts"
            )
        if 1 in sizes:
            warnings.append(f"frame_{index}: isolated opaque pixel(s)")
        frames.append(
            {
                "index": index,
                "pixel_sha256": sha256(image.tobytes()),
                "bounds": list(image.getchannel("A").getbbox()),
                "visible_pixels": sum(sizes),
                "component_sizes": sizes,
            }
        )
    unique = len({item["pixel_sha256"] for item in frames})
    if unique < model.frame_count:
        warnings.append(f"Only {unique} distinct poses in {model.frame_count} frames; inspect movement cadence")
    seam = sum(
        a != b
        for a, b in zip(right[-1].get_flattened_data(), right[0].get_flattened_data(), strict=True)
    )
    return {
        "status": "candidate",
        "errors": [],
        "warnings": warnings,
        "unique_poses": unique,
        "loop_seam_changed_pixels": seam,
        "frames": frames,
        "rgb565_bytes_both_directions": model.width * model.height * 2 * 2 * model.frame_count,
        "mask_bytes_both_directions": ((model.width * model.height + 7) // 8) * 2 * model.frame_count,
    }
