"""Explicit pixel-art leg patches, authorized by the user on 2026-09-08.

Run with /usr/bin/python3 (Pillow). Never writes production assets or headers.
Every polygon uses integer coordinates and colors already in its keyframe.
"""
from pathlib import Path
import hashlib
import json
import runpy
import struct
import zlib

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CODEC = runpy.run_path(str(ROOT / 'tools/generate_tft_assets.py'))
BG = (255, 0, 255)
DURATION = 140
EXPECTED_SOURCES = {
    'dragon_walk_left_01': 'f1fd656b7fa30248145745f7d46c37d95d40d602f62cdd3057468ad78382432a',
    'dragon_walk_left_02': '7ae6d6a95a9a1d05f18a046fec915cbb6a66d1516b17549d01bc71c578d65267',
}


def load(name):
    path = ROOT / 'assets/tft' / (name + '.bmp')
    assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_SOURCES[name], 'Reference changed: review the pixel patches before rebuilding'
    w, h, pixels = CODEC['read_color_bmp'](path)
    clean, count = CODEC['normalize_transparent_matte'](w, h, pixels)
    assert (w, h) == (112, 112)
    image = Image.new('RGB', (w, h))
    image.putdata(clean)
    return image, dict(path=str(path.relative_to(ROOT)),
                       sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                       normalized_background_pixels=count)


def paint(image, polygons, colors):
    draw = ImageDraw.Draw(image)
    for color, points in polygons:
        draw.polygon(points, fill=colors[color])


a, source_a = load('dragon_walk_left_01')
b, source_b = load('dragon_walk_left_02')
compression = a.copy()
# Front leg only: retain the hip at (44, 92), bend the shin toward the body,
# plant a flatter foot two pixels lower. The lifted rear leg stays untouched.
paint(compression, [
    ('bg', [(30, 96), (40, 94), (54, 96), (56, 107), (30, 107)]),
    ('outline', [(43, 92), (49, 93), (53, 96), (53, 99), (56, 102),
                 (56, 106), (54, 107), (35, 107), (33, 105), (33, 102),
                 (37, 100), (39, 97), (42, 96)]),
    ('orange', [(43, 94), (48, 95), (51, 97), (51, 100), (53, 102),
                (53, 104), (36, 104), (36, 102), (40, 101), (42, 97)]),
    ('red', [(48, 96), (51, 98), (51, 101), (54, 103), (54, 105),
             (48, 105), (48, 102), (46, 100)]),
    ('claw', [(35, 103), (38, 103), (38, 105), (35, 105)]),
    ('claw', [(40, 103), (43, 103), (43, 105), (40, 105)]),
    ('claw', [(45, 103), (47, 103), (47, 105), (45, 105)]),
], dict(bg=BG, outline=(4, 13, 41), orange=(252, 103, 3),
        red=(251, 52, 3), claw=(253, 234, 104)))
# Preserve the original square claws and their shading. This is a selected
# toe block placed on the hand-drawn shin, not a transform of the whole sprite.
compression.paste(a.crop((32, 99, 55, 106)), (34, 101))

lift = b.copy()
# Front leg only: fold the toe back under the shin for recovery. Retain the
# supporting rear foot, tail, belly, arms and the whole head from keyframe B.
paint(lift, [
    ('bg', [(40, 97), (54, 97), (64, 102), (64, 109), (40, 109)]),
    ('outline', [(54, 96), (62, 96), (64, 98), (64, 101), (62, 104),
                 (60, 105), (47, 105), (45, 103), (45, 100), (48, 98),
                 (53, 98)]),
    ('orange', [(56, 96), (61, 97), (62, 99), (61, 102), (59, 103),
                (48, 103), (47, 101), (50, 100), (54, 100)]),
    ('red', [(61, 98), (62, 98), (62, 101), (60, 104),
             (54, 104), (54, 103), (59, 102)]),
    ('claw', [(47, 101), (49, 101), (49, 103), (47, 103)]),
    ('claw', [(51, 101), (53, 101), (53, 103), (51, 103)]),
    ('claw', [(55, 101), (57, 101), (57, 103), (55, 103)]),
], dict(bg=BG, outline=(4, 10, 39), orange=(252, 98, 3),
        red=(252, 54, 3), claw=(253, 225, 92)))
lift.paste(b.crop((41, 99, 64, 109)), (45, 96))

frames = [a, compression, b, lift]
bases = [a, a, b, b]
labels = ['01 Contact (A)', '02 Amortissement', '03 Passage (B)', '04 Elevation']
# Historical B reaches row 108, A row 105. Placement aligns their ground
# without redrawing either approved keyframe or resampling its pixels.
offsets = [0, 0, -1, 0]
(OUT / 'bmp').mkdir(exist_ok=True)


def isolated(image, opaque):
    data = list(image.getdata())
    result = set()
    for y in range(1, 111):
        for x in range(1, 111):
            if (data[y * 112 + x] != BG) != opaque:
                continue
            adjacent = [data[(y + dy) * 112 + x + dx] != BG
                        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]]
            if all(value != opaque for value in adjacent):
                result.add((x, y))
    return result


report = []
for number, (frame, base) in enumerate(zip(frames, bases), 1):
    pixels, original = list(frame.getdata()), list(base.getdata())
    palette = set(original)
    assert set(pixels) <= palette, 'New color outside the source keyframe palette'
    changed = [(i % 112, i // 112) for i, (p, q) in enumerate(zip(pixels, original)) if p != q]
    assert all(30 <= x <= 68 and 92 <= y <= 109 for x, y in changed)
    assert frame.crop((0, 0, 112, 92)).tobytes() == base.crop((0, 0, 112, 92)).tobytes()
    # Lower belly extends beneath protected row 91. Its pale/yellow clusters
    # must also remain identical; claws lie outside this torso region.
    for y in range(92, 97):
        for x in range(40, 62):
            color = base.getpixel((x, y))
            if color[0] > 200 and color[1] > 140:
                assert frame.getpixel((x, y)) == color
    added_dots = isolated(frame, True) - isolated(base, True)
    added_holes = isolated(frame, False) - isolated(base, False)
    assert not added_dots, ('New isolated opaque pixels', added_dots)
    assert not added_holes, ('New one-pixel holes', added_holes)
    assert not any(c != BG and CODEC['is_magenta_matte'](c) for c in pixels)
    visible = [(i % 112, i // 112) for i, c in enumerate(pixels) if c != BG]
    packed = [CODEC['rgb565'](*p) for p in pixels]
    encoded = CODEC['compress_pixels'](packed)
    assert CODEC['decompress_pixels'](encoded, 112 * 112) == packed
    path = OUT / 'bmp' / f'dragon_walk_left_{number:02}_candidate.bmp'
    frame.save(path)
    data = path.read_bytes()
    assert struct.unpack_from('<H', data, 28)[0] == 24
    assert struct.unpack_from('<I', data, 30)[0] == 0
    report.append(dict(file=path.name, duration_ms=DURATION,
                       reference='A' if number <= 2 else 'B',
                       changed_pixels=len(changed), protected_rows='0..91 identical to reference',
                       visible_pixels=len(visible), native_ground=max(y for x,y in visible),
                       y_offset=offsets[number-1],
                       ground=max(y for x,y in visible)+offsets[number-1],
                       palette_colors=len(set(pixels)), added_isolated_pixels=len(added_dots),
                       added_one_pixel_holes=len(added_holes), rle_bytes=len(encoded),
                       crc32=f"{zlib.crc32(CODEC['pixels_as_bytes'](packed)):08X}",
                       sha256=hashlib.sha256(data).hexdigest()))
areas = [r['visible_pixels'] for r in report]
grounds = [r['ground'] for r in report]
assert max(areas) / min(areas) <= 1.06
assert max(grounds) - min(grounds) <= 2
assert len({frame.tobytes() for frame in frames}) == 4

for name, background in [('cyan', (0, 255, 255)), ('green', (0, 255, 0)),
                         ('dark', (24, 34, 56))]:
    views = []
    for frame, offset in zip(frames, offsets):
        view = Image.new('RGB', frame.size)
        view.putdata([background if c == BG else c for c in frame.getdata()])
        positioned = Image.new('RGB', frame.size, background)
        positioned.paste(view, (0, offset))
        views.append(positioned)
    sheet = Image.new('RGB', (112 * 4, 128), background)
    for i, view in enumerate(views):
        sheet.paste(view, (i * 112, 0))
        ImageDraw.Draw(sheet).text((i * 112 + 3, 115), labels[i], fill=(0, 0, 0) if name != 'dark' else (255,255,255))
    sheet.save(OUT / f'sheet-{name}-1x.png')
    sheet.resize((1792, 512), Image.Resampling.NEAREST).save(OUT / f'sheet-{name}-4x.png')
    # Single exact global palette avoids per-frame quantization/color shimmer.
    palette_colors = sorted(set(c for view in views for c in view.getdata()))
    palette = Image.new('P', (1,1))
    palette.putpalette([channel for c in palette_colors for channel in c] + [0] * (768 - 3*len(palette_colors)))
    color_index = {color: index for index, color in enumerate(palette_colors)}
    for scale in [1,4]:
        gif_frames = []
        for view in views:
            indexed = Image.new('P', view.size)
            indexed.putpalette(palette.getpalette())
            indexed.putdata([color_index[color] for color in view.getdata()])
            gif_frames.append(indexed.resize((112*scale,112*scale), Image.Resampling.NEAREST))
        gif_frames[0].save(OUT / f'walk-{name}-{scale}x.gif', save_all=True,
                           append_images=gif_frames[1:], duration=DURATION,
                           loop=0, disposal=2, optimize=False)

(OUT / 'validation.json').write_text(json.dumps(dict(
    status='rejected_by_user', sources=[source_a,source_b],
    duration_ms=DURATION, cycle_ms=DURATION*4, area_ratio=max(areas)/min(areas),
    ground_delta=max(grounds)-min(grounds), frames=report), indent=2)+'\n')
print(json.dumps(dict(frames=4, cycle_ms=560, changed=[r['changed_pixels'] for r in report],
                      areas=areas, ground=grounds, rle_round_trip='PASS')))
