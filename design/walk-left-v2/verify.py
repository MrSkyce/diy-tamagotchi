"""Check motion constraints and final pixel files, not just frame count."""
from pathlib import Path
import hashlib
import json
import math
import runpy
import struct
from collections import deque
from PIL import Image

FOLDER=Path(__file__).resolve().parent
ROOT=FOLDER.parents[1]
report=json.loads((FOLDER/'validation.json').read_text())
codec=runpy.run_path(str(ROOT/'tools/generate_tft_assets.py'))
source=ROOT/report['source']
assert hashlib.sha256(source.read_bytes()).hexdigest()==report['source_sha256']
w,h,original=codec['read_color_bmp'](source)
original,_=codec['normalize_transparent_matte'](w,h,original)
reference=Image.new('RGB',(w,h));reference.putdata(original)
assert len(report['frames'])==8
assert sum(e['duration_ms'] for e in report['frames'])==960
stats=[]
unique_frames=set()
for i,entry in enumerate(report['frames']):
    for key,length in [('near_leg',10),('far_leg',10),('near_arm',8),('far_arm',8)]:
        a,b,c=entry[key]
        assert abs(math.dist(a,b)-length)<1e-8
        assert abs(math.dist(b,c)-length)<1e-8
        # Integer raster anchors inevitably round: bound the actual visible
        # segment error instead of asserting that a float rig alone is enough.
        a,b,c=[tuple(round(v) for v in p) for p in (a,b,c)]
        assert abs(math.dist(a,b)-length)<=math.sqrt(2)
        assert abs(math.dist(b,c)-length)<=math.sqrt(2)
    assert entry['near_lift']==0 or entry['far_lift']==0
    assert (entry['near_phase']+4)%8==entry['far_phase']
    for side in ['near','far']:
        assert entry[f'{side}_leg'][2][1]+5==106-entry[f'{side}_lift']
    path=FOLDER/'bmp'/entry['file'];raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==entry['sha256']
    assert struct.unpack_from('<H',raw,28)[0]==24
    assert struct.unpack_from('<I',raw,30)[0]==0
    w,h,pixels=codec['read_color_bmp'](path)
    assert (w,h)==(112,112) and set(pixels)<=set(original)
    unique_frames.add(bytes(v for p in pixels for v in p))
    assert max(i//112 for i,p in enumerate(pixels) if p!=(255,0,255))==106
    assert not any(p!=(255,0,255) and codec['is_magenta_matte'](p) for p in pixels)
    remaining={j for j,p in enumerate(pixels) if p!=(255,0,255)}
    components=[]
    while remaining:
        start=remaining.pop();queue=deque([start]);size=0
        while queue:
            j=queue.popleft();size+=1;x=j%112;y=j//112
            for yy in range(max(0,y-1),min(112,y+2)):
                for xx in range(max(0,x-1),min(112,x+2)):
                    neighbor=yy*112+xx
                    if neighbor in remaining:remaining.remove(neighbor);queue.append(neighbor)
        components.append(size)
    assert len(components)==1, ('detached fragment',i,components)
    frame=Image.open(path).convert('RGB');bob=entry['bob']
    assert frame.crop((0,bob+3,112,bob+68)).tobytes()==reference.crop((0,3,112,68)).tobytes()
    for y in range(1,111):
        for x in range(1,111):
            opaque=pixels[y*112+x]!=(255,0,255)
            neighbors=[pixels[(y+dy)*112+x+dx]!=(255,0,255)
                       for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]]
            assert not all(v!=opaque for v in neighbors), ('isolated pixel/hole',i,x,y)
    rgb565=[codec['rgb565'](*p) for p in pixels]
    encoded=codec['compress_pixels'](rgb565)
    assert codec['decompress_pixels'](encoded,112*112)==rgb565
    stats.append(dict(file=path.name,visible_pixels=entry['visible_pixels'],rle_bytes=len(encoded)))
assert len(unique_frames)==8
assert max(s['visible_pixels'] for s in stats)/min(s['visible_pixels'] for s in stats)<=1.06
# For each continuous stance interval, world ankle X is constant while the
# body traverses left. Check both legs, including the far stance across wrap.
max_world_drift=0
max_raster_drift=0
for side,start in [('near',0),('far',4)]:
    positions=[]
    raster_positions=[]
    for t in range(start,start+5):
        entry=report['frames'][t%8]
        assert entry[f'{side}_lift']==0
        positions.append(entry[f'{side}_leg'][2][0]-t*report['travel_per_frame'])
        raster_positions.append(round(entry[f'{side}_leg'][2][0])-round(t*report['travel_per_frame']))
    max_world_drift=max(max_world_drift,max(positions)-min(positions))
    max_raster_drift=max(max_raster_drift,max(raster_positions)-min(raster_positions))
assert max_world_drift<1e-8
assert max_raster_drift<=1
# Check exported GIF pixels as well as pose lengths and timing.
for name,bg in [('dark',(24,34,56)),('cyan',(0,255,255)),('green',(0,255,0))]:
    for scale in [1,4]:
        gif=Image.open(FOLDER/f'walk-{name}-{scale}x.gif')
        assert gif.n_frames==8 and gif.info['loop']==0
        for i,e in enumerate(report['frames']):
            gif.seek(i);assert gif.info['duration']==120
            frame=Image.open(FOLDER/'bmp'/e['file']).convert('RGB')
            expected=Image.new('RGB',(112,112))
            expected.putdata([bg if c==(255,0,255) else c for c in frame.getdata()])
            expected=expected.resize((112*scale,112*scale),Image.Resampling.NEAREST)
            assert gif.convert('RGB').tobytes()==expected.tobytes()
travel=Image.open(FOLDER/'walk-travel-2x.gif')
assert travel.n_frames==24
for t in range(24):
    travel.seek(t);assert travel.info['duration']==120
    sprite=Image.open(FOLDER/'bmp'/report['frames'][t%8]['file']).convert('RGB')
    # The sprite region ends immediately before the ground line. Inspect every
    # opaque pixel in that region at the prescribed world position.
    rendered=travel.convert('RGB')
    origin=144-round(t*report['travel_per_frame'])
    for y in range(112):
        for x in range(112):
            c=sprite.getpixel((x,y))
            if c!=(255,0,255):
                assert rendered.getpixel(((origin+x)*2,y*2))==c
approved=json.loads((ROOT/'design/mascots-v1/APPROVAL.json').read_text())
for model in approved['models']:
    assert hashlib.sha256((ROOT/model['file']).read_bytes()).hexdigest()==model['sha256']
result=dict(status='host_checks_passed_visual_review_pending',
    fixed_leg_segments_px=[10,10],fixed_arm_segments_px=[8,8],
    theoretical_stance_drift_px=max_world_drift,ground=106,
    raster_stance_drift_px=max_raster_drift,
    area_ratio=max(s['visible_pixels'] for s in stats)/min(s['visible_pixels'] for s in stats),frames=stats)
(FOLDER/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
