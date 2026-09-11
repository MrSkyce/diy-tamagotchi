import shutil
from pathlib import Path

from . import __version__
from .config import load_model
from .errors import AnimationError
from .preview import write_previews
from .renderer import render
from .storage import input_inventory, inventory, output_path, transaction, verify_bundle, write_json
from .validators import report, sha256


def validate(config: Path):
    model = load_model(config)
    directions = render(model)
    return model, directions, report(model, directions)


def generate(config: Path, root: Path, force=False):
    model, directions, validation = validate(config)
    target = output_path(root, "generated", model.id)
    with transaction(target, force, model.inputs) as temporary:
        for direction, frames in directions.items():
            folder = temporary / direction
            folder.mkdir()
            write_previews(frames, model.palette, model.duration_ms, folder)
        write_json(temporary / "validation.json", validation)
        manifest = {
            "schema_version": 1,
            "generator_version": __version__,
            "status": "candidate",
            "mascot": model.id,
            "animation": "walk",
            "frame_count": model.frame_count,
            "width": model.width,
            "height": model.height,
            "duration_ms": model.duration_ms,
            "ground_y": model.ground_y,
            "palette": [list(rgb) for rgb in model.palette],
            "inputs": input_inventory(model),
            "files": inventory(temporary),
        }
        write_json(temporary / "manifest.json", manifest)
    return target


def generate_all(root: Path, force=False):
    configs = sorted((root / "mascots").glob("*/mascot.yaml"))
    if not configs:
        raise AnimationError(f"No mascots/*/mascot.yaml in {root}")
    # Validate every model and destination before publishing any member.
    ids = []
    for config in configs:
        model, _, _ = validate(config)
        ids.append(model.id)
        target = output_path(root, "generated", model.id)
        if target.exists() and not force:
            raise AnimationError(f"Output already exists: {target}; use --force")
    if len(set(ids)) != len(ids):
        raise AnimationError("Duplicate mascot identifiers in batch")
    return [generate(config, root, force) for config in configs]


def approve(root: Path, mascot: str, reviewed_by: str, force=False):
    if not reviewed_by.strip():
        raise AnimationError("A nonempty --reviewed-by is required")
    source = output_path(root, "generated", mascot)
    manifest = verify_bundle(source)
    if manifest["mascot"] != mascot:
        raise AnimationError("Candidate mascot does not match requested mascot")
    target = output_path(root, "approved", mascot)
    with transaction(target, force) as temporary:
        for name in [*manifest["files"], "manifest.json"]:
            dest = temporary / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, dest)
        verify_bundle(temporary)
        write_json(
            temporary / "approval.json",
            {
                "schema_version": 1,
                "reviewed_by": reviewed_by.strip(),
                "scope": f"{manifest['frame_count']}-frame walk, both directions",
                "manifest_sha256": sha256((temporary / "manifest.json").read_bytes()),
            },
        )
    return target
