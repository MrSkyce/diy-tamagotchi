from pathlib import Path

from sprite_animator.golden import test_golden as verify_golden


def test_reviewed_fixture_pixels():
    assert verify_golden(Path(__file__).resolve().parents[1]) == 24
