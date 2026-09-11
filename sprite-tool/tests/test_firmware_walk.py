import json
import runpy
import shutil
import subprocess
from pathlib import Path

import pytest
from sprite_animator.validators import sha256

REPO = Path(__file__).parents[2]


def test_native_walk_clock_and_visibility(tmp_path):
    compiler = shutil.which("c++")
    if not compiler:
        pytest.skip("Native C++ compiler unavailable")
    source = r'''
    #include "walk_cycle.h"
    #include <assert.h>
    int main() {
      WalkCycle w;
      assert(w.x() == 64 && w.phase() == 0);
      assert(w.update(100, true));
      assert(!w.update(219, true));
      assert(w.update(220, true) && w.x() == 67 && w.phase() == 1);
      for (unsigned i=2; i<=20; ++i) w.update(100+i*120, true);
      assert(w.x() == 124 && w.right());
      w.update(2620, true);
      assert(w.x() == 124 && !w.right() && w.turning() && w.phase() == 0);
      w.update(2740, true);
      assert(w.x() == 121 && !w.turning() && w.phase() == 1);
      int before=w.x();
      w.update(100000, false);
      assert(w.x() == before);
      w.update(200000, true);
      assert(w.x() == before && w.phase() == 0);
      w.update(300000, true); // stall: one pose and one 3-pixel step, never teleport
      assert(w.x() == before-3 && w.phase() == 1);
      for (unsigned i=1; i<=500; ++i) {
        int previous=w.x();
        w.update(300000+i*120, true);
        assert(w.x() >= 4 && w.x() <= 124);
        int delta=w.x()-previous;
        assert(delta == 0 || delta == 3 || delta == -3);
      }
      WalkCycle overflow;
      overflow.update(0xFFFFFFD0u, true);
      assert(!overflow.update(0x20u, true));
      assert(overflow.update(0x48u, true));
      assert(overflow.x() == 67);
      assert(homeWalkEnabled(true,true,30,25,25,49,false));
      assert(!homeWalkEnabled(false,true,50,50,50,0,false));
      assert(!homeWalkEnabled(true,false,50,50,50,0,false));
      assert(!homeWalkEnabled(true,true,29,50,50,0,false));
      assert(!homeWalkEnabled(true,true,50,24,50,0,false));
      assert(!homeWalkEnabled(true,true,50,50,24,0,false));
      assert(!homeWalkEnabled(true,true,50,50,95,0,false));
      assert(!homeWalkEnabled(true,true,50,50,50,50,false));
      assert(!homeWalkEnabled(true,true,50,50,50,0,true));
    }
    '''
    executable = tmp_path / "walk-check"
    result = subprocess.run([compiler, "-std=c++11", "-Wall", "-Wextra", "-Werror",
                             "-x", "c++", "-I", str(REPO / "include"), "-", "-o", str(executable)],
                            input=source, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert subprocess.run([str(executable)]).returncode == 0


def test_production_frames_match_human_approved_export():
    folder = REPO / "assets/tft"
    approval = json.loads((folder / "rigged_walk_approval.json").read_text())
    assert approval["status"] == "approved_skinned_walk"
    assert approval["evidence"] == "oui, validé."
    assert len(approval["files_sha256"]) == 16
    for name, digest in approval["files_sha256"].items():
        assert sha256((folder / name).read_bytes()) == digest
    source = REPO / "sprite-tool/approved/dragon_rigged/walk/manifest.json"
    assert sha256(source.read_bytes()) == approval["approved_manifest_sha256"]


def test_production_validator_covers_all_eight_and_keeps_legacy_rules():
    codec = runpy.run_path(str(REPO / "tools/generate_tft_assets.py"))
    assets = {}
    for file in (REPO / "assets/tft").glob("*.bmp"):
        w, h, pixels = codec["read_color_bmp"](file)
        pixels, _ = codec["normalize_transparent_matte"](w, h, pixels)
        assets[file.stem] = (w, h, pixels)
    codec["validate_asset_scale"](assets)
    missing = dict(assets)
    del missing["dragon_rigged_walk_left_08"]
    with pytest.raises(ValueError, match="missing animation"):
        codec["validate_asset_scale"](missing)
    wrong = dict(assets)
    wrong["dragon_idle1"] = assets["dragon_rigged_walk_left_01"]
    with pytest.raises(ValueError, match="5000..7300"):
        codec["validate_asset_scale"](wrong)
