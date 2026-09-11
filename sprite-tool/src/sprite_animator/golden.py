from pathlib import Path

from .errors import AnimationError
from .pipeline import validate
from .storage import read_json
from .validators import sha256


def test_golden(root: Path):
    """Compare against checked-in expectations; never create or update them."""
    golden = root / "tests" / "golden" / "pixels.json"
    expected = read_json(golden)
    checked = 0
    for name, directions in expected.items():
        _, rendered, _ = validate(root / "examples" / "mascots" / name / "mascot.yaml")
        actual = {
            direction: [sha256(im.tobytes()) for im in frames]
            for direction, frames in rendered.items()
        }
        if actual != directions:
            raise AnimationError(
                f"Golden mismatch: {name}; inspect pixels before changing baseline"
            )
        checked += 12
    if not checked:
        raise AnimationError("Golden reference is empty")
    return checked
