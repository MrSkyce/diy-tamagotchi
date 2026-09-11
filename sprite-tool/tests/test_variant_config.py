import json
import shutil
from pathlib import Path

import pytest

from sprite_animator.errors import AnimationError
from sprite_animator.variant_config import load_variant
from sprite_animator.variants import build

ROOT = Path(__file__).resolve().parents[1]


def test_all_historical_variant_configs_remain_valid():
    configs = list((ROOT / "mascots").glob("*/variant-skin-v*.json"))
    assert len(configs) == 20
    for config in configs:
        load_variant(config)


@pytest.mark.parametrize("change", [
    {"typo": 1}, {"id": "../bad"}, {"source": "../profile.png"},
    {"body_type": "unknown"}, {"source_hip": [True, 82]},
    {"source_hip": [57.0, 82]},
    {"source_hip": [112, 82]}, {"rig_overrides": {"hip_y": True}},
    {"rig_overrides": {"hip_y": 80.5}}, {"rig_overrides": {"thigh": 1}},
    {"rig_overrides": {"bob": [0]}}, {"rig_overrides": {"unknown": 1}},
    {"palette": ["#100020", "#100020"]}, {"palette": ["#FF00FF"]},
    {"foot_style": "unknown"}, {"continuous_ankle": "yes"},
    {"source_sha256": "0" * 64}, {"parts": {"head": [], "tail": []}},
    {"colors": {}},
])
def test_invalid_variant_leaves_no_output(tmp_path, change):
    original = ROOT / "mascots/yellow_bird"
    shutil.copytree(original / "art-candidates", tmp_path / "art-candidates")
    spec = json.loads((original / "variant-skin-v4.json").read_text())
    spec.update(change)
    config = tmp_path / "config.json"
    config.write_text(json.dumps(spec))
    with pytest.raises(AnimationError):
        build(config, tmp_path / "result")
    assert not (tmp_path / "result").exists()


@pytest.mark.parametrize("raw", ['{"id": 1, "id": 2}', '{"x": NaN}',
                                 '{"x": Infinity}', '{"x": -Infinity}', '{'])
def test_malformed_json_is_explicit(tmp_path, raw):
    config = tmp_path / "config.json"
    config.write_text(raw)
    with pytest.raises(AnimationError):
        load_variant(config)
