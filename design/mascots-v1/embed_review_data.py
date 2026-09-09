"""Embed exact BMP pixel values into the local review; never modify images."""
import base64
import json
from pathlib import Path
import runpy

folder = Path(__file__).resolve().parent
root = folder.parents[1]
reader = runpy.run_path(str(root / 'tools/generate_tft_assets.py'))['read_color_bmp']
sources = [('Dragon — référence', root / 'assets/tft/dragon_idle1.bmp')]
sources += [(name, folder / 'bmp' / (key + '_idle_01_candidate.bmp')) for key, name in [
    ('blue_cat', 'Chat Bleu'), ('red_dog', 'Chien Rouge'),
    ('green_mouse', 'Souris Verte'), ('yellow_bird', 'Oiseau Jaune'),
    ('purple_salamander', 'Salamandre Violette')]]
data = []
for name, source in sources:
    width, height, pixels = reader(source)
    assert (width, height) == (112, 112)
    raw = bytes(channel for pixel in pixels for channel in pixel)
    data.append(dict(name=name, rgb=base64.b64encode(raw).decode('ascii')))
target = folder / 'review.html'
text = target.read_text()
start = text.index('/*MASCOT_DATA*/') + len('/*MASCOT_DATA*/')
end = text.index(';\n', start)
target.write_text(text[:start] + json.dumps(data, ensure_ascii=False) + text[end:])
assert target.stat().st_size < 1_000_000
print('Embedded six exact 112x112 BMP pixel arrays; source images unchanged.')
