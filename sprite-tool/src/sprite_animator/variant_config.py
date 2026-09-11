"""Strict input boundary for the species skin compiler; never approves artwork."""

import json
from dataclasses import asdict

from jsonschema import Draft202012Validator, validators
from PIL import Image

from .errors import AnimationError
from .mannequin import DEFAULT_RIG, rig_from_data
from .storage import safe_member
from .validators import sha256


def _object(properties, required=None):
    return {"type": "object", "properties": properties, "additionalProperties": False,
            "required": list(properties) if required is None else required}


COLOR = {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"}
POINT = {"type": "array", "minItems": 2, "maxItems": 2,
         "items": {"type": "integer", "minimum": 0, "maximum": 111}}
POLYGON = {"type": "array", "minItems": 3, "maxItems": 112, "items": POINT}
FIELDS = {
    "id": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"},
    "source": {"type": "string", "minLength": 1},
    "source_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    "body_type": {"enum": ["bird", "rounded_paws"]},
    "source_hip": POINT,
    "rig_overrides": _object({key: {} for key in asdict(DEFAULT_RIG)}, []),
    "colors": _object(dict.fromkeys(("outline", "near", "far", "belly", "foot"), COLOR)),
    "palette": {"type": "array", "minItems": 1, "maxItems": 253,
                "uniqueItems": True, "items": COLOR},
    "parts": _object(dict.fromkeys(("head", "tail", "wing"), POLYGON), ["head", "tail"]),
    "foot_style": {"enum": [prefix + species for prefix in ("", "cartoon_")
                             for species in ("cat", "dog", "mouse", "bird", "salamander")]},
    "continuous_ankle": {"type": "boolean"},
}
SCHEMA = _object(FIELDS, [key for key in FIELDS if key not in
                          ("foot_style", "continuous_ankle")])
StrictValidator = validators.extend(
    Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER.redefine(
        "integer", lambda checker, value: type(value) is int),
)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AnimationError(f"Duplicate variant key: {key}")
        result[key] = value
    return result


def _nonfinite(value):
    raise AnimationError(f"Non-finite variant number: {value}")


def load_variant(path):
    try:
        spec = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique,
                          parse_constant=_nonfinite)
        error = next(StrictValidator(SCHEMA).iter_errors(spec), None)
        if error:
            location = ".".join(map(str, error.absolute_path)) or "root"
            raise AnimationError(f"{path}: {location}: {error.message}")
        # JSON-normalize tuple defaults for the shared strict vector/type checker.
        data = json.loads(json.dumps(asdict(DEFAULT_RIG)))
        data.update(spec["rig_overrides"])
        rig = rig_from_data(data)
        palette = [color.upper() for color in spec["palette"]]
        if len(set(palette)) != len(palette):
            raise AnimationError("Duplicate variant palette color")
        if "#FF00FF" in palette or any(c.upper() not in palette
                                         for c in spec["colors"].values()):
            raise AnimationError("Variant colors must belong to palette; magenta is reserved")
        if spec["body_type"] == "bird" and "wing" not in spec["parts"]:
            raise AnimationError("Bird requires a wing mask")
        if spec.get("continuous_ankle") and "foot_style" not in spec:
            raise AnimationError("continuous_ankle requires foot_style")
        source = safe_member(path.parent, spec["source"])
        if sha256(source.read_bytes()) != spec["source_sha256"]:
            raise AnimationError("Profile changed since direction review")
        with Image.open(source) as image:
            if (image.format != "PNG" or max(image.size) > 4096
                    or getattr(image, "n_frames", 1) != 1):
                raise AnimationError("Variant source must be a single PNG no larger than 4096px")
            if image.convert("RGBA").getchannel("A").getextrema() != (255, 255):
                raise AnimationError("Variant profile requires an opaque background")
        return spec, rig, source
    except (OSError, ValueError, RecursionError, Image.DecompressionBombError) as error:
        raise AnimationError(f"Cannot load variant {path}: {error}") from error
