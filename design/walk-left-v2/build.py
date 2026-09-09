"""Eight-pose walk study: constant-length two-bone limbs, no sprite stretching.

Art reference: the unchanged dragon_walk_left_01 BMP.
Motion reference: SLYNYRD Pixelblog 50 (principles, no tutorial pixels copied).
"""
from pathlib import Path
import hashlib
import json
import math
import runpy
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BG = (255,0,255)
CODEC = runpy.run_path(str(ROOT/'tools/generate_tft_assets.py'))
SOURCE = ROOT/'assets/tft/dragon_walk_left_01.bmp'
SOURCE_SHA = 'f1fd656b7fa30248145745f7d46c37d95d40d602f62cdd3057468ad78382432a'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
w,h,pixels = CODEC['read_color_bmp'](SOURCE)
pixels,_ = CODEC['normalize_transparent_matte'](w,h,pixels)
source = Image.new('RGB',(w,h)); source.putdata(pixels)
NAVY=(4,13,41); ORANGE=(252,103,3); RED=(251,52,3)
YELLOW=(253,234,104); SHADE=(157,66,24)
GROUND=106
DURATION=120
# Leftward travel: a planted foot moves right in sprite coordinates.
FOOT_X=[-9,-4.5,0,4.5,9,4.5,0,-4.5]
FOOT_LIFT=[0,0,0,0,0,4,7,4]
BOB=[0,1,-1,-2,0,1,-1,-2]
STRIDE_PER_FRAME=4.5
PHASES=['Contact G','Appui G','Passage D','Avance D',
        'Contact D','Appui D','Passage G','Avance G']


def ik(hip, ankle, upper=10, lower=10, bend=-1):
    dx,dy=ankle[0]-hip[0],ankle[1]-hip[1]
    distance=math.hypot(dx,dy)
    assert abs(upper-lower) < distance <= upper+lower, ('unreachable',hip,ankle)
    projection=(upper*upper-lower*lower+distance*distance)/(2*distance)
    height=math.sqrt(max(0,upper*upper-projection*projection))
    knee=(hip[0]+projection*dx/distance+bend*height*dy/distance,
          hip[1]+projection*dy/distance-bend*height*dx/distance)
    assert abs(math.dist(hip,knee)-upper)<1e-9
    assert abs(math.dist(knee,ankle)-lower)<1e-9
    return hip,knee,ankle


def point(p): return tuple(round(v) for v in p)


def limb(image, joints, far=False, width=9):
    draw=ImageDraw.Draw(image)
    pts=[point(p) for p in joints]
    draw.line(pts, fill=NAVY, width=width)
    for x,y in pts[1:-1]:
        radius=(width-1)//2
        draw.rectangle((x-radius,y-radius,x+radius,y+radius),fill=NAVY)
    draw.line(pts, fill=RED if far else ORANGE, width=width-4)


def paste_opaque(target, patch, xy):
    mask=Image.new('L',patch.size)
    mask.putdata([0 if c==BG else 255 for c in patch.getdata()])
    target.paste(patch,xy,mask)


# Head/wings are one rigid layer. Lower trunk and tail are selected explicitly;
# both original arms and legs are removed from the moving body layer.
body=Image.new('RGB',(112,112),BG)
body.paste(source.crop((0,0,112,70)),(0,0))
trunk_mask=Image.new('1',(112,112))
ImageDraw.Draw(trunk_mask).polygon([(40,66),(65,66),(65,83),(62,89),
                                  (58,95),(51,95),(43,90),(40,84)],fill=1)
body.paste(source,(0,0),trunk_mask)
for box in [(84,70,112,95),(76,84,112,95)]:
    body.paste(source.crop(box),box[:2])
# The outer edge of the old right hand lies just inside the first tail crop.
# Remove that vertical fragment explicitly; it is not part of the tail.
ImageDraw.Draw(body).rectangle((84,70,89,83),fill=BG)
# Reconnect the tail root behind the body; never retain the old rear foot
# while extracting the tail from the flattened reference.
ImageDraw.Draw(body).polygon([(62,84),(78,86),(80,92),(72,94),(63,90)],fill=NAVY)
ImageDraw.Draw(body).polygon([(64,85),(78,87),(78,90),(72,91),(64,88)],fill=RED)
body.paste(source,(0,0),trunk_mask)

# Rigid toe block: identical silhouette and color pixels throughout the cycle.
foot=source.crop((32,99,55,106))
# The historical rear paw is tilted in the air and cannot be used unchanged
# as a planted sole. Draw one smaller, flat far paw with the same color vocabulary.
far_toe_rows=[
    '......DDDDDD..',
    '.....DOOOORDD.',
    '...DDOOOORRRD.',
    '.DDOOOORRRRRD.',
    'DYYDYYDYYORRD.',
    'DYYDYYDYYRRRD.',
    '.DDDDDDDDDDDD.',
]
far_foot=Image.new('RGB',(14,7),BG)
toe_colors={'.':BG,'D':NAVY,'O':RED,'R':SHADE,'Y':YELLOW}
far_foot.putdata([toe_colors[c] for row in far_toe_rows for c in row])
hand=source.crop((24,78,35,84))
frames=[]; rigs=[]; checks=[]
for i in range(8):
    near_phase=i; far_phase=(i+4)%8
    bob=BOB[i]
    near_hip=(51,87+bob); far_hip=(61,85+bob)
    near_ankle=(51+FOOT_X[near_phase],GROUND-5-FOOT_LIFT[near_phase])
    far_ankle=(61+FOOT_X[far_phase],GROUND-5-FOOT_LIFT[far_phase])
    near=ik(near_hip,near_ankle)
    far=ik(far_hip,far_ankle)
    # Opposite arm/leg swings, with the elbow solved at fixed lengths too.
    arm_swing=FOOT_X[i]*0.5
    near_arm=ik((42,70+bob),(42-arm_swing,83+bob),8,8,bend=1)
    far_arm=ik((64,70+bob),(64+arm_swing,83+bob),8,8,bend=1)
    frame=Image.new('RGB',(112,112),BG)
    limb(frame,far,far=True)
    paste_opaque(frame,far_foot,(round(far_ankle[0])-10,round(far_ankle[1])-1))
    limb(frame,far_arm,far=True,width=7)
    paste_opaque(frame,hand,(round(far_arm[2][0])-6,round(far_arm[2][1])-2))
    limb(frame,near)
    paste_opaque(frame,foot,(round(near_ankle[0])-17,round(near_ankle[1])-1))
    paste_opaque(frame,body,(0,bob))
    limb(frame,near_arm,width=7)
    paste_opaque(frame,hand,(round(near_arm[2][0])-6,round(near_arm[2][1])-2))
    # Two manually inspected one-pixel seams at layer junctions.
    for x,y in {4:[(66,76)],7:[(50,93)]}.get(i,[]):
        frame.putpixel((x,y),NAVY)
    frames.append(frame)
    # Anatomical guide is a separate review artifact, never a production sprite.
    rig=Image.new('RGB',(112,112),(24,34,56));d=ImageDraw.Draw(rig)
    d.line((0,GROUND,111,GROUND),fill=(110,120,140))
    for joints,color in [(far,(70,170,255)),(near,(255,190,60)),
                          (far_arm,(70,170,255)),(near_arm,(255,190,60))]:
        d.line([point(p) for p in joints],fill=color,width=2)
        for p in joints:
            x,y=point(p);d.rectangle((x-1,y-1,x+1,y+1),fill=color)
    d.line([point(near_hip),point(far_hip)],fill=(255,255,255),width=2)
    d.line((52,68+bob,56,86+bob),fill=(255,255,255),width=2)
    rigs.append(rig)
    # The shoulder/arm work stays below the head. Assert identity in its entirety.
    assert frame.crop((0,bob+3,112,bob+68)).tobytes()==source.crop((0,3,112,68)).tobytes()
    assert set(frame.getdata()) <= set(source.getdata())
    visible=[(j%112,j//112) for j,c in enumerate(frame.getdata()) if c!=BG]
    assert max(y for x,y in visible)==GROUND
    checks.append(dict(phase=PHASES[i],duration_ms=DURATION,y_offset=0,
                       bob=bob,near_phase=near_phase,far_phase=far_phase,
                       near_leg=near,far_leg=far,near_arm=near_arm,far_arm=far_arm,
                       near_lift=FOOT_LIFT[near_phase],far_lift=FOOT_LIFT[far_phase],
                       visible_pixels=len(visible),ground=GROUND))


def export_gif(path, images, duration=DURATION, scale=4):
    colors=sorted(set(c for im in images for c in im.getdata()))
    assert len(colors)<=256
    lookup={c:i for i,c in enumerate(colors)}
    palette=[v for c in colors for v in c]+[0]*(768-3*len(colors))
    indexed=[]
    for im in images:
        p=Image.new('P',im.size);p.putpalette(palette)
        p.putdata([lookup[c] for c in im.getdata()])
        indexed.append(p.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST))
    indexed[0].save(path,save_all=True,append_images=indexed[1:],duration=duration,
                    loop=0,disposal=2,optimize=False)


(OUT/'bmp').mkdir(exist_ok=True)
for i,(frame,entry) in enumerate(zip(frames,checks),1):
    path=OUT/'bmp'/f'dragon_walk_left_{i:02}_candidate.bmp'
    frame.save(path)
    entry['file']=path.name
    entry['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
for name,bg in [('dark',(24,34,56)),('cyan',(0,255,255)),('green',(0,255,0))]:
    views=[]
    for frame in frames:
        view=Image.new('RGB',frame.size)
        view.putdata([bg if c==BG else c for c in frame.getdata()]);views.append(view)
    for scale in [1,4]:export_gif(OUT/f'walk-{name}-{scale}x.gif',views,scale=scale)
    sheet=Image.new('RGB',(112*4,128*2),bg)
    for i,view in enumerate(views):
        x=(i%4)*112;y=(i//4)*128
        sheet.paste(view,(x,y))
        ImageDraw.Draw(sheet).text((x+2,y+114),f'{i+1} {PHASES[i]}',fill=(255,255,255) if name=='dark' else NAVY)
    sheet.resize((1344,768),Image.Resampling.NEAREST).save(OUT/f'sheet-{name}-3x.png')
export_gif(OUT/'rig-4x.gif',rigs)
rig_sheet=Image.new('RGB',(448,224),(24,34,56))
for i,rig in enumerate(rigs):rig_sheet.paste(rig,((i%4)*112,(i//4)*112))
rig_sheet.resize((1344,672),Image.Resampling.NEAREST).save(OUT/'rig-sheet-3x.png')
# A moving view reveals sliding: body travels left by 4.5px/frame, matching
# the rightward motion of the stance ankle within each sprite.
travel=[]
for i in range(24):
    view=Image.new('RGB',(256,128),(24,34,56));d=ImageDraw.Draw(view)
    d.line((0,107,255,107),fill=(90,100,115))
    for x in range(0,256,12):d.line((x,108,x,111),fill=(90,100,115))
    paste_opaque(view,frames[i%8],(144-round(i*STRIDE_PER_FRAME),0))
    travel.append(view)
export_gif(OUT/'walk-travel-2x.gif',travel,scale=2)
(OUT/'validation.json').write_text(json.dumps(dict(status='candidate_requires_visual_review',
    sources=[dict(path=str(SOURCE.relative_to(ROOT)),sha256=SOURCE_SHA)],
    source=str(SOURCE.relative_to(ROOT)),source_sha256=SOURCE_SHA,
    motion_reference='https://www.slynyrd.com/blog/2024/5/24/pixelblog-50-human-walk-cycle',
    duration_ms=DURATION,cycle_ms=8*DURATION,leg_segments=[10,10],
    arm_segments=[8,8],travel_per_frame=STRIDE_PER_FRAME,frames=checks),indent=2)+'\n')
print('Built eight constant-length-limb poses, rig and travel previews.')
