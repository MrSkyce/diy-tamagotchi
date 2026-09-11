import json
from pathlib import Path

from sprite_animator.cli import main
from sprite_animator.storage import inventory, verify_bundle

ROOT = Path(__file__).parents[1]


def test_current_six_walks_rebuild_without_promoting_or_overwriting(tmp_path, capsys):
    before = inventory(ROOT / "approved")
    dest = tmp_path / "rebuilt"
    assert main(["generate-rigged", str(dest), "--root", str(ROOT)]) == 0
    capsys.readouterr()
    report = json.loads((dest / "verification.json").read_text())
    assert report["status"] == "six_rebuilt_walks_match_approved_png_bytes"
    assert report["frames_checked"] == 96
    assert not report["approval_created"] and not report["production_exported"]
    assert len(report["walks"]) == 6
    for walk in report["walks"]:
        folder = dest / "generated" / walk["mascot"] / "walk"
        assert verify_bundle(folder)["frame_count"] == 8
        assert len(walk["matching_png_sha256"]) == 16
    assert not (dest / "approved").exists()
    assert not (dest / "firmware-export").exists()
    output_before = inventory(dest)
    assert main(["generate-rigged", str(dest), "--root", str(ROOT)]) == 2
    assert "already exists" in capsys.readouterr().err
    assert inventory(dest) == output_before
    assert inventory(ROOT / "approved") == before
