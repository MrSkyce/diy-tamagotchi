import argparse
import json
import sys
from pathlib import Path

from .demo import init_demo
from .errors import AnimationError
from .exporters.bundle import export
from .golden import test_golden
from .pipeline import approve, generate, generate_all, validate
from .preparation import prepare_layers
from .references import prepare_references
from .rigged_batch import rebuild


def parser():
    result = argparse.ArgumentParser(
        prog="sprite-anim", description="Offline pixel-art animation compiler"
    )
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("validate", "generate"):
        command = commands.add_parser(name)
        command.add_argument("config", type=Path)
    commands.add_parser("generate-all")
    rigged = commands.add_parser("generate-rigged", help="Rebuild six current walks and compare approvals")
    rigged.add_argument("destination", type=Path, help="New output directory; never overwrite")
    layers = commands.add_parser(
        "prepare-layers", help="Extract manually specified layers without changing pixels"
    )
    layers.add_argument("spec", type=Path)
    approval = commands.add_parser(
        "approve", help="Record explicit human review of generated frames"
    )
    approval.add_argument("mascot")
    approval.add_argument("--reviewed-by", required=True)
    exporter = commands.add_parser("export")
    exporter.add_argument("mascot")
    exporter.add_argument("--format", choices=("rgb565", "cpp", "bmp"), default="rgb565")
    exporter.add_argument("--byte-order", choices=("little", "big"), default="little")
    exporter.add_argument("--transparency", choices=("key", "mask"), default="key")
    exporter.add_argument("--key", default="#FF00FF", help="RGB transparency key (#RRGGBB)")
    commands.add_parser("test-golden")
    references = commands.add_parser(
        "prepare-references", help="Prepare exact RGBA copies of the six approved references"
    )
    references.add_argument("--repo", type=Path, required=True)
    demo = commands.add_parser(
        "init-demo", help="Create two geometric fixtures, not production mascots"
    )
    demo.add_argument("destination", type=Path)
    for name, command in commands.choices.items():
        if name != "init-demo":
            command.add_argument(
                "--root", type=Path, default=Path.cwd(), help="Workspace root (default: cwd)"
            )
        if name not in ("test-golden", "init-demo", "prepare-references", "prepare-layers"):
            command.add_argument("--animation", choices=("walk",), default="walk")
        if name in (
            "generate",
            "generate-all",
            "approve",
            "export",
            "prepare-references",
            "prepare-layers",
        ):
            command.add_argument(
                "--force", action="store_true", help="Replace output, keeping previous folder"
            )
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "validate":
            _, _, result = validate(args.config)
        elif args.command == "generate":
            result = {"generated": str(generate(args.config, args.root, args.force))}
        elif args.command == "generate-all":
            result = {"generated": [str(p) for p in generate_all(args.root, args.force)]}
        elif args.command == "generate-rigged":
            result = {"verified_rebuild": str(rebuild(args.root, args.destination))}
        elif args.command == "approve":
            result = {
                "approved": str(approve(args.root, args.mascot, args.reviewed_by, args.force))
            }
        elif args.command == "export":
            if len(args.key) != 7 or not args.key.startswith("#"):
                raise AnimationError("--key must be #RRGGBB")
            try:
                key = tuple(bytes.fromhex(args.key[1:]))
            except ValueError as error:
                raise AnimationError("--key must be #RRGGBB") from error
            result = {
                "exported": str(
                    export(
                        args.root,
                        args.mascot,
                        fmt=args.format,
                        byte_order=args.byte_order,
                        transparency=args.transparency,
                        key=key,
                        force=args.force,
                    )
                )
            }
        elif args.command == "init-demo":
            result = {"demo": str(init_demo(args.destination))}
        elif args.command == "prepare-references":
            result = {"references": str(prepare_references(args.repo, args.root, args.force))}
        elif args.command == "prepare-layers":
            result = {"layers": str(prepare_layers(args.spec, args.root, args.force))}
        else:
            result = {"golden_frames_checked": test_golden(args.root)}
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (AnimationError, OSError) as error:
        print(
            json.dumps({"status": "error", "errors": [str(error)]}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
