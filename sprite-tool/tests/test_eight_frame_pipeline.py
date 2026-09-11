import json
import shutil
import subprocess

import pytest
import yaml
from PIL import Image
from sprite_animator.config import load_model
from sprite_animator.errors import AnimationError
from sprite_animator.exporters.bundle import export
from sprite_animator.pipeline import approve, generate
from sprite_animator.storage import verify_bundle


def extend_to_eight(config):
    data = yaml.safe_load(config.read_text())
    profile = (config.parent / data["animation_profiles"]["walk"]).resolve()
    data = yaml.safe_load(profile.read_text())
    data["frames"] = 8
    for track in data["tracks"].values():
        track.extend(track[:2])
    profile.write_text(yaml.safe_dump(data))
    return profile


def test_eight_frame_roundtrip_all_formats(project):
    root, config = project
    extend_to_eight(config)
    data = yaml.safe_load(config.read_text())
    data["canvas"].update(width=112, height=112)
    config.write_text(yaml.safe_dump(data))
    model = load_model(config)
    assert model.frame_count == 8
    target = generate(config, root)
    manifest = verify_bundle(target)
    assert manifest["frame_count"] == 8
    assert len(list((target / "right").glob("frame_*.png"))) == 8
    with Image.open(target / "right/walk-1x.gif") as gif:
        elapsed = 0
        for i in range(gif.n_frames):
            gif.seek(i)
            with Image.open(target / f"right/frame_{(elapsed // 120) % 8:02}.png") as frame:
                rgb = Image.new("RGB", frame.size, (24, 34, 56))
                rgb.paste(frame, mask=frame.getchannel("A"))
                assert gif.convert("RGB").tobytes() == rgb.tobytes()
            elapsed += gif.info["duration"]
        assert elapsed == 8 * 120 * 3
    with pytest.raises(AnimationError):
        export(root, model.id)
    # Synthetic fixture in pytest's temporary workspace only, not real art approval.
    approved = approve(root, model.id, "synthetic eight-frame test")
    assert json.loads((approved / "approval.json").read_text())["scope"].startswith("8-frame")
    exported = export(root, model.id, transparency="mask")
    assert (exported / "right.rgb565").stat().st_size == 8 * 112 * 112 * 2
    assert (exported / "right.mask").stat().st_size == 8 * 112 * 112 // 8
    exported = export(root, model.id, fmt="cpp", transparency="mask", force=True)
    assert "frame_count = 8" in (exported / "right.h").read_text()
    assert json.loads((exported / "metadata.json").read_text())["frame_count"] == 8
    compiler = shutil.which("c++")
    if compiler:
        result = subprocess.run([compiler, "-std=c++11", "-x", "c++", "-I", str(exported),
                                 "-", "-o", str(root / "eight-check")], input=
                                '#include "right.h"\nstatic_assert(demo_biped_walk_right_frame_count == 8, "eight");\nint main() {}\n',
                                text=True, capture_output=True)
        assert result.returncode == 0, result.stderr
    exported = export(root, model.id, fmt="bmp", force=True)
    assert len(list(exported.glob("*.bmp"))) == 16
    with Image.open(exported / "demo_biped_walk_right_08.bmp") as bmp:
        assert bmp.size == (112, 112)
        assert bmp.getpixel((0, 0)) == (255, 0, 255)
    (approved / "left/frame_07.png").unlink()
    with pytest.raises(AnimationError):
        export(root, model.id, force=True)


@pytest.mark.parametrize("count", [6, 7])
def test_track_length_must_match_declared_eight(project, count):
    _, config = project
    profile = extend_to_eight(config)
    data = yaml.safe_load(profile.read_text())
    key = next(iter(data["tracks"]))
    data["tracks"][key] = data["tracks"][key][:count]
    profile.write_text(yaml.safe_dump(data))
    with pytest.raises(AnimationError, match="match the declared"):
        load_model(config)


def test_phase_and_last_override_for_eight_only(project):
    root, config = project
    data = yaml.safe_load(config.read_text())
    data["layers"][0]["phase"] = 7
    data["overrides"] = {"walk": {"frame_7": {data["layers"][0]["id"]: {}}}}
    config.write_text(yaml.safe_dump(data))
    with pytest.raises(AnimationError, match="phase exceeds"):
        load_model(config)
    # Find profile directly because the deliberately invalid config cannot load yet.
    profile = (config.parent / data["animation_profiles"]["walk"]).resolve()
    profile_data = yaml.safe_load(profile.read_text())
    profile_data["frames"] = 8
    for track in profile_data["tracks"].values():
        track.extend(track[:2])
    profile.write_text(yaml.safe_dump(profile_data))
    assert load_model(config).frame_count == 8
