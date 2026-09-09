"""Read-only host checks of the five design candidates; no production generation."""
from pathlib import Path
import hashlib
import importlib.util
import json
import struct
import zlib

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('assets', root / 'tools/generate_tft_assets.py')
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)
paths = sorted((Path(__file__).parent / 'bmp').glob('*.bmp'))
assert len(paths) == 5
report = []
for path in paths:
    w, h, pixels = assets.read_color_bmp(path)
    assert (w, h) == (112, 112)
    assert assets.TRANSPARENT_RGB in pixels
    assert len(set(pixels)) <= 24
    rgb565 = [assets.rgb565(*p) for p in pixels]
    encoded = assets.compress_pixels(rgb565)
    decoded = assets.decompress_pixels(encoded, w * h)
    assert decoded == rgb565
    opaque = [(i % w, i // w) for i, p in enumerate(pixels)
              if p != assets.TRANSPARENT_RGB]
    data = path.read_bytes()
    report.append(dict(file=path.name, size=[w, h],
        bits=struct.unpack_from('<H', data, 28)[0],
        compression=struct.unpack_from('<I', data, 30)[0],
        colors=len(set(pixels)), visible_pixels=len(opaque),
        bounds=[min(x for x,y in opaque), min(y for x,y in opaque),
                max(x for x,y in opaque), max(y for x,y in opaque)],
        residual_matte=sum(p != assets.TRANSPARENT_RGB and assets.is_magenta_matte(p)
                           for p in pixels),
        rgb565_bytes=len(rgb565)*2, rle_bytes=len(encoded), round_trip='PASS',
        crc32=f'{zlib.crc32(assets.pixels_as_bytes(decoded)):08X}',
        sha256=hashlib.sha256(data).hexdigest()))
print(json.dumps(dict(scope='Candidate format and host RLE only; not art or hardware approval',
                      candidates=report), indent=2))
