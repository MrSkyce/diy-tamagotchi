import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]


def test_native_registry_resolves_all_96_approved_frames(tmp_path):
    compiler = shutil.which("c++")
    if not compiler:
        pytest.skip("Native C++ compiler unavailable")
    source = r'''
    #include "mascot_walks.h"
    #include <cassert>
    #include <cstdio>
    int main() {
      static_assert(WalkCycle::kFrames == 8, "approved frame count");
      static_assert(WalkCycle::kDurationMs == 120, "approved cadence");
      static_assert(WalkCycle::kStepPixels == 3, "approved travel");
      for (unsigned species=0; species<6; ++species) {
        auto mascot = static_cast<MascotId>(species);
        assert(mascotWalk(mascot).label[0]);
        for (unsigned direction=0; direction<2; ++direction) {
          for (unsigned phase=0; phase<8; ++phase) {
            auto frame = mascotWalkFrame(mascot, direction, phase);
            assert(static_cast<unsigned>(frame) < TFT_ASSET_COUNT);
            assert(frame == mascotWalkFrame(mascot, direction, phase+8));
            std::printf("%u\n", static_cast<unsigned>(frame));
          }
        }
      }
      assert(mascotWalkFrame(static_cast<MascotId>(255), true, 255) ==
             mascotWalkFrame(MascotId::DRAGON, true, 7));
    }
    '''
    binary = tmp_path / "registry-test"
    built = subprocess.run([compiler, "-std=c++11", "-Wall", "-Wextra", "-Werror",
                            "-x", "c++", "-I", str(ROOT / "include"), "-", "-o", str(binary)],
                           input=source, capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    ids = [int(line) for line in run.stdout.splitlines()]
    catalog = [p.stem for p in sorted((ROOT / "assets/tft").glob("*.bmp"))]
    prefixes = ("dragon_rigged", "blue_cat_rigged_feet_v4", "red_dog_rigged_feet_v4",
                "green_mouse_rigged_feet_v4", "yellow_bird_rigged_feet_v4",
                "purple_salamander_rigged_feet_v4")
    expected = [f"{prefix}_walk_{direction}_{i:02}" for prefix in prefixes
                for direction in ("left", "right") for i in range(1, 9)]
    assert [catalog[index] for index in ids] == expected
    assert len(set(ids)) == 96
