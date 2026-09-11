"""Rebuild the six current rigged walks and compare to frozen approvals."""

from pathlib import Path

from .errors import AnimationError
from .pipeline import generate
from .skin import prepare
from .storage import identifier, read_json, safe_member, transaction, verify_bundle, write_json
from .validators import sha256
from .variants import build


def rebuild(root, destination):
    root = Path(root).resolve()
    selection = read_json(root / "rigged-walks.json")
    if not isinstance(selection, list) or len(selection) != 6:
        raise AnimationError("Expected six current rigged walks")
    seen, members = set(), []
    for entry in selection:
        if not isinstance(entry, dict) or entry.keys() != {"mascot", "config", "compiler"}:
            raise AnimationError("Invalid rigged selection entry")
        mascot = identifier(entry["mascot"])
        if mascot in seen or entry["compiler"] not in ("dragon", "variants"):
            raise AnimationError("Duplicate mascot or unsupported compiler")
        seen.add(mascot)
        config = safe_member(root, entry["config"])
        approved = root / "approved" / mascot / "walk"
        manifest = verify_bundle(approved)
        review = read_json(safe_member(approved, "approval.json"))
        digest = sha256((approved / "manifest.json").read_bytes())
        if (manifest["mascot"] != mascot or manifest["frame_count"] != 8
                or review.get("manifest_sha256") != digest or not review.get("reviewed_by")):
            raise AnimationError(f"Invalid approval: {mascot}")
        members.append((entry, config, approved, digest))
    reports = []
    # A fresh destination only. Neither candidates nor approvals are replaced.
    with transaction(Path(destination), inputs=(root,)) as folder:
        for entry, config, approved, digest in members:
            mascot = entry["mascot"]
            prepared = folder / "prepared" / mascot
            (prepare if entry["compiler"] == "dragon" else build)(config, prepared)
            generated = generate(prepared / "mascot.yaml", folder)
            actual = verify_bundle(generated)
            if actual["mascot"] != mascot:
                raise AnimationError(f"Selection/config identifier mismatch: {mascot}")
            files = {}
            for direction in ("right", "left"):
                for i in range(8):
                    name = f"{direction}/frame_{i:02}.png"
                    data = (generated / name).read_bytes()
                    if data != (approved / name).read_bytes():
                        raise AnimationError(f"Rebuilt frame differs from approval: {mascot}/{name}")
                    files[name] = sha256(data)
            reports.append({"mascot": mascot, "approved_manifest_sha256": digest,
                            "matching_png_sha256": files})
        write_json(folder / "verification.json", {
            "status": "six_rebuilt_walks_match_approved_png_bytes", "frames_checked": 96,
            "approval_created": False, "production_exported": False, "walks": reports,
        })
    return Path(destination)
