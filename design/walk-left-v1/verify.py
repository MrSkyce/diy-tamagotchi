"""Independently verify files and exact GIF playback exported by build.py."""
from pathlib import Path
import hashlib
import json
import runpy

from PIL import Image

folder = Path(__file__).resolve().parent
root = folder.parents[1]
report = json.loads((folder / 'validation.json').read_text())
codec = runpy.run_path(str(root / 'tools/generate_tft_assets.py'))
assert len(report['frames']) == 4
assert sum(e['duration_ms'] for e in report['frames']) == 560
references = []
for source in report['sources']:
    assert hashlib.sha256((root / source['path']).read_bytes()).hexdigest() == source['sha256']
    w,h,p = codec['read_color_bmp'](root / source['path'])
    normalized, _ = codec['normalize_transparent_matte'](w,h,p)
    image = Image.new('RGB',(w,h)); image.putdata(normalized)
    references.append(image)
for i,e in enumerate(report['frames']):
    path = folder / 'bmp' / e['file']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == e['sha256']
    image = Image.open(path).convert('RGB')
    reference = references[0 if i < 2 else 1]
    assert image.crop((0,0,112,92)).tobytes() == reference.crop((0,0,112,92)).tobytes()
    if i in (0,2):
        assert image.tobytes() == reference.tobytes()
for name,bg in [('cyan',(0,255,255)),('green',(0,255,0)),('dark',(24,34,56))]:
    for scale in (1,4):
        gif = Image.open(folder / f'walk-{name}-{scale}x.gif')
        assert gif.n_frames == 4 and gif.info['loop'] == 0
        for i,entry in enumerate(report['frames']):
            gif.seek(i)
            assert gif.info['duration'] == entry['duration_ms']
            frame = Image.open(folder / 'bmp' / entry['file']).convert('RGB')
            view = Image.new('RGB',(112,112))
            view.putdata([bg if c == (255,0,255) else c for c in frame.getdata()])
            expected = Image.new('RGB',(112,112),bg)
            expected.paste(view,(0,entry['y_offset']))
            expected = expected.resize((112*scale,112*scale),Image.Resampling.NEAREST)
            assert gif.convert('RGB').tobytes() == expected.tobytes(), (name,scale,i)
approved = json.loads((root / 'design/mascots-v1/APPROVAL.json').read_text())
for model in approved['models']:
    assert hashlib.sha256((root/model['file']).read_bytes()).hexdigest() == model['sha256']
print('PASS: four poses; six exact-color GIFs; timing and offsets; locked reference regions; two historical BMPs and five approved models unchanged')
