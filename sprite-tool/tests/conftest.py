import pytest
from sprite_animator.demo import fixture


@pytest.fixture
def project(tmp_path):
    config = fixture(tmp_path / "mascots" / "demo_biped")
    return tmp_path, config
