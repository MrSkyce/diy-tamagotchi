from pathlib import Path

from sprite_animator.pipeline import generate
from sprite_animator.production_check import check
from sprite_animator.skin import prepare
from sprite_animator.storage import inventory


def test_approved_real_cycle_passes_production_scale_without_global_relaxation(tmp_path):
    repo = Path(__file__).parents[2]
    before = {name: inventory(repo / name) for name in ("assets/tft", "include")}
    prepared = prepare(repo / "sprite-tool/mascots/dragon/skin.json", tmp_path / "prepared")
    candidate = generate(prepared / "mascot.yaml", tmp_path)
    candidate_before = inventory(candidate)
    result = check(candidate, repo)
    assert result["codec_roundtrip"] == "passed"
    assert result["production_asset_validation"] == "passed"
    assert result["production_validation_error"] is None
    assert result["production_visible_pixel_range"] == [5000, 7300]
    assert len(result["candidate_frames"]) == 16
    assert result["approved_rigged_walk_visible_pixel_range"] == [2306, 2378]
    assert result["current_catalog_count"] == 129
    assert result["proposed_catalog_count"] == 129
    assert not (tmp_path / "approved").exists()
    assert not (tmp_path / "firmware-export").exists()
    assert inventory(candidate) == candidate_before
    assert {name: inventory(repo / name) for name in before} == before
