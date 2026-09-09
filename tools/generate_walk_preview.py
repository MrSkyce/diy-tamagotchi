"""Build only the opt-in walk diagnostic; do not touch the W25Q64 catalogue."""
from pathlib import Path
import json
import hashlib
import runpy

Import('env')
root = Path(env['PROJECT_DIR'])
folder = root / 'design/walk-left-v2'
codec = runpy.run_path(str(root / 'tools/generate_tft_assets.py'))
manifest = json.loads((folder / 'validation.json').read_text())
if manifest['status'] == 'rejected_by_user':
    raise ValueError('This walk candidate was rejected; do not build its diagnostic')
for reference in manifest['sources']:
    if hashlib.sha256((root / reference['path']).read_bytes()).hexdigest() != reference['sha256']:
        raise ValueError('Walk reference changed; review the candidates before compiling')
arrays = []
steps = []
for index, entry in enumerate(manifest['frames']):
    path = folder / 'bmp' / entry['file']
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
        raise ValueError(f'{path.name}: rerun the candidate validator first')
    w, h, pixels = codec['read_color_bmp'](path)
    if (w,h) != (112,112) or entry['y_offset'] not in (-1,0):
        raise ValueError('Unsupported preview geometry')
    rgb = [codec['rgb565'](*p) for p in pixels]
    name = f'WALK_PIXELS_{index}'
    lines = [', '.join(f'0x{p:04X}' for p in rgb[i:i+16]) for i in range(0,len(rgb),16)]
    arrays.append(f'const uint16_t {name}[] PROGMEM = {{\n' + ',\n'.join(lines) + '\n};')
    steps.append(f"{{{index}, {entry['duration_ms']}, {entry['y_offset']}}}")
output = Path(env.subst('$BUILD_DIR'))
output.mkdir(parents=True, exist_ok=True)
header = '#pragma once\n#include <Arduino.h>\n#include "animation_player.h"\n'
header += '\n'.join(arrays)
header += '\nconst uint16_t* const WALK_PIXELS[] = {' + ','.join(f'WALK_PIXELS_{i}' for i in range(len(arrays))) + '};\n'
header += 'constexpr AnimationFrame WALK_STEPS[] = {' + ','.join(steps) + '};\n'
header += f'constexpr AnimationClip WALK_CLIP = {{WALK_STEPS, {len(steps)}, true}};\n'
(output / 'generated_walk_preview.h').write_text(header)
env.Append(CPPPATH=[str(output)])
print(f'Walk preview: {len(steps)} verified frames; production catalogue unchanged')
