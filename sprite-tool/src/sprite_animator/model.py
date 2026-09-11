from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass(frozen=True)
class Step:
    offset: tuple[int, int] = (0, 0)
    pose: str | None = None


@dataclass(frozen=True)
class Layer:
    id: str
    anchor: tuple[int, int]
    pivot: tuple[int, int]
    z_index: int
    parent: str | None
    track: str | None
    phase: int
    offset_scale: tuple[int, int]
    mirror: bool
    images: dict[str, Image.Image]


@dataclass(frozen=True)
class Model:
    id: str
    width: int
    height: int
    ground_y: int
    ground_tolerance: int
    palette: tuple[tuple[int, int, int], ...]
    duration_ms: int
    layers: tuple[Layer, ...]
    tracks: dict[str, tuple[Step, ...]]
    overrides: dict[int, dict[str, Step]]
    inputs: tuple[Path, ...]
    config_path: Path
    frame_count: int = 6
