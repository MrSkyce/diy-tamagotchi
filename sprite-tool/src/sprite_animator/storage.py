import json
import os
import re
import shutil
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path

from PIL import Image

from .errors import AnimationError
from .validators import sha256


def json_bytes(data) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def write_json(path, data):
    path.write_bytes(json_bytes(data))


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", value):
        raise AnimationError(f"Invalid identifier: {value!r}")
    return value


def output_path(root: Path, area: str, mascot: str) -> Path:
    root = root.resolve()
    target = root / area / identifier(mascot) / "walk"
    # Refuse symlink destinations, including an ancestor redirecting writes.
    for path in (target, *target.parents):
        if path == root:
            break
        if path.is_symlink():
            raise AnimationError(f"Symlink output path is forbidden: {path}")
    return target


@contextmanager
def transaction(target: Path, force=False, inputs=()):
    """Publish a complete folder; explicit replacements preserve the old folder."""
    target = target.absolute()
    if target.resolve() != target:
        raise AnimationError(f"Symlink output path is forbidden: {target}")
    for path in inputs:
        if path == target or target in path.parents:
            raise AnimationError(f"Output would replace an input: {path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    lock = target.parent / f".{target.name}.lock"
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise AnimationError(f"Output is locked by another operation: {lock}") from error
    temporary = None
    backup = None
    try:
        if target.exists() and not force:
            raise AnimationError(
                f"Output already exists: {target}; use --force to replace explicitly"
            )
        if target.exists() and not target.is_dir():
            raise AnimationError(f"Output is not a directory: {target}")
        temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
        yield temporary
        if target.exists():
            backup = target.parent / f".{target.name}.previous-{uuid.uuid4().hex}"
            target.rename(backup)
        try:
            temporary.rename(target)
        except OSError:
            if backup:
                backup.rename(target)
            raise
    finally:
        if temporary and temporary.exists():
            shutil.rmtree(temporary)
        lock.rmdir()


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise AnimationError(f"Cannot read {path}: {error}") from error


def safe_member(folder, name):
    if not isinstance(name, str) or not name:
        raise AnimationError("Artifact member must be a nonempty path")
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise AnimationError(f"Invalid artifact member: {name}")
    path = folder / relative
    if path.resolve() != path.absolute() or not path.is_file():
        raise AnimationError(f"Missing or symlink artifact member: {name}")
    return path


def inventory(folder):
    return {
        str(path.relative_to(folder)): sha256(path.read_bytes())
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def verify_bundle(folder: Path):
    manifest = read_json(safe_member(folder, "manifest.json"))
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != 1
        or manifest.get("animation") != "walk"
        or type(manifest.get("frame_count")) is not int
        or manifest.get("frame_count") not in (6, 8)
        or manifest.get("status") != "candidate"
    ):
        raise AnimationError("Invalid or unsupported candidate manifest")
    identifier(manifest.get("mascot", ""))
    for dimension in ("width", "height"):
        value = manifest.get(dimension)
        if type(value) is not int or not 1 <= value <= 512:
            raise AnimationError(f"Invalid manifest {dimension}")
    duration = manifest.get("duration_ms")
    if type(duration) is not int or not 10 <= duration <= 65530 or duration % 10:
        raise AnimationError("Invalid manifest duration_ms")
    palette = manifest.get("palette")
    if (
        not isinstance(palette, list)
        or not 1 <= len(palette) <= 253
        or any(
            not isinstance(rgb, list)
            or len(rgb) != 3
            or any(type(c) is not int or not 0 <= c <= 255 for c in rgb)
            for rgb in palette
        )
    ):
        raise AnimationError("Invalid manifest palette")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise AnimationError("Missing candidate file inventory")
    required = {
        f"{direction}/frame_{i:02}.png" for direction in ("right", "left") for i in range(manifest["frame_count"])
    }
    required.add("validation.json")
    required.update(
        f"{direction}/{name}"
        for direction in ("right", "left")
        for name in ("sheet.png", "sheet-4x.png", "walk-1x.gif", "walk-4x.gif")
    )
    if required != files.keys():
        raise AnimationError("Incomplete animation: files must match declared frame count in both directions")
    for name, digest in files.items():
        if sha256(safe_member(folder, name).read_bytes()) != digest:
            raise AnimationError(f"Artifact changed since validation: {name}")
    report = read_json(folder / "validation.json")
    if (
        not isinstance(report, dict)
        or report.get("errors") != []
        or report.get("status") != "candidate"
    ):
        raise AnimationError("Animation has not passed validation")
    allowed = {tuple(rgb) for rgb in palette}
    for direction in ("right", "left"):
        for index in range(manifest["frame_count"]):
            name = f"{direction}/frame_{index:02}.png"
            try:
                with Image.open(folder / name) as image:
                    if (
                        image.format != "PNG"
                        or image.mode != "RGBA"
                        or image.size != (manifest["width"], manifest["height"])
                    ):
                        raise AnimationError(f"{name}: dimensions or PNG mode differ from manifest")
                    if any(
                        p[3] not in (0, 255) or (p[3] and p[:3] not in allowed)
                        for p in image.get_flattened_data()
                    ):
                        raise AnimationError(f"{name}: invalid alpha or palette")
            except OSError as error:
                raise AnimationError(f"Cannot read {name}: {error}") from error
    return manifest


def input_inventory(model):
    return {
        os.path.relpath(path, model.config_path.parent): sha256(path.read_bytes())
        for path in model.inputs
    }
