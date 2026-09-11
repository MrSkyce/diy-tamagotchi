import json
import shutil
import subprocess
import sys

import pytest
from PIL import Image
from sprite_animator.demo import fixture
from sprite_animator.errors import AnimationError
from sprite_animator.exporters.bundle import export
from sprite_animator.pipeline import approve, generate, generate_all
from sprite_animator.storage import inventory, transaction


def test_generation_reproducible_and_preview_timing(project):
    root, config = project
    inputs = inventory(config.parent)
    target = generate(config, root)
    first = inventory(target)
    other = root / "other-workspace"
    assert inventory(generate(config, other)) == first
    assert inventory(config.parent) == inputs
    with Image.open(target / "right" / "sheet.png") as sheet:
        assert sheet.size == (192, 32)
    with Image.open(target / "right" / "walk-1x.gif") as gif:
        assert gif.info["loop"] == 0
        elapsed = 0
        for i in range(gif.n_frames):
            gif.seek(i)
            expected_index = (elapsed // 120) % 6
            with Image.open(target / "right" / f"frame_{expected_index:02}.png") as png:
                expected = Image.new("RGB", png.size, (24, 34, 56))
                expected.paste(png, mask=png.getchannel("A"))
            assert gif.convert("RGB").tobytes() == expected.tobytes()
            elapsed += gif.info["duration"]
        assert elapsed == 6 * 120 * 3


def test_approval_integrity_and_non_overwrite(project):
    root, config = project
    with pytest.raises(AnimationError):
        export(root, "demo_biped")
    target = generate(config, root)
    with pytest.raises(AnimationError, match="already exists"):
        generate(config, root)
    with pytest.raises(AnimationError):
        export(root, "demo_biped")
    approved = approve(root, "demo_biped", "test fixture reviewer")
    approved_before = inventory(approved)
    exported = export(root, "demo_biped")
    assert (exported / "right.rgb565").stat().st_size == 32 * 32 * 2 * 6
    with pytest.raises(AnimationError, match="already exists"):
        approve(root, "demo_biped", "reviewer")
    generate(config, root, force=True)
    assert inventory(approved) == approved_before
    with pytest.raises(AnimationError, match="already exists"):
        export(root, "demo_biped")
    # Replacing an output preserves the exact previous folder for recovery.
    export(root, "demo_biped", fmt="cpp", force=True)
    assert list(exported.parent.glob(".walk.previous-*/right.rgb565"))
    (approved / "right/frame_00.png").write_bytes(b"tampered")
    with pytest.raises(AnimationError, match="changed since validation"):
        export(root, "demo_biped", force=True)
    (target / "left/frame_05.png").unlink()
    with pytest.raises(AnimationError, match="Missing"):
        approve(root, "demo_biped", "reviewer", force=True)


def test_generate_all_six_distinct_fixture_ids(tmp_path):
    for index in range(6):
        name = f"fixture_{index}"
        fixture(tmp_path / "mascots" / name, name, quadruped=index % 2 == 1)
    results = generate_all(tmp_path)
    assert len(results) == 6
    assert all(len(list((path / "right").glob("frame_*.png"))) == 6 for path in results)


def test_transaction_rolls_back_and_protects_sources(tmp_path):
    target = tmp_path / "output"
    with pytest.raises(RuntimeError):
        with transaction(target) as temporary:
            (temporary / "partial").write_text("incomplete")
            raise RuntimeError("simulated error")
    assert not target.exists()
    assert not list(tmp_path.iterdir())
    target.mkdir()
    source = target / "source.png"
    source.write_text("keep")
    with pytest.raises(AnimationError, match="replace an input"):
        with transaction(target, force=True, inputs=[source]):
            pass
    assert source.read_text() == "keep"


def test_cli_success_and_error_json(project):
    root, config = project
    result = subprocess.run(
        [sys.executable, "-m", "sprite_animator", "generate", str(config), "--root", str(root)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["generated"]
    result = subprocess.run(
        [sys.executable, "-m", "sprite_animator", "export", "../escape", "--root", str(root)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert json.loads(result.stderr)["status"] == "error"


def test_symlink_output_rejected(project, tmp_path):
    root, config = project
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (root / "generated").symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(AnimationError, match="Symlink"):
        generate(config, root)
    assert not list(elsewhere.iterdir())


def test_batch_preflight_no_partial_output(project):
    root, _ = project
    bad = fixture(root / "mascots" / "bad", "bad")
    (bad.parent / "head.png").unlink()
    with pytest.raises(AnimationError):
        generate_all(root)
    assert not (root / "generated").exists()


def test_cpp_export_compiles(project):
    compiler = shutil.which("c++")
    if not compiler:
        pytest.skip("C++ compiler unavailable")
    root, config = project
    generate(config, root)
    approve(root, "demo_biped", "test fixture reviewer")
    target = export(root, "demo_biped", fmt="cpp", transparency="mask")
    source = '#include "right.h"\n#include "left.h"\nstatic_assert(demo_biped_walk_right_width == 32, "width");\nint main() { return demo_biped_walk_left_frame_count == 6 ? 0 : 1; }\n'
    result = subprocess.run(
        [
            compiler,
            "-std=c++11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-x",
            "c++",
            "-I",
            str(target),
            "-",
            "-o",
            str(root / "check"),
        ],
        input=source,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert subprocess.run([str(root / "check")]).returncode == 0
