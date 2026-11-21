#!/usr/bin/env python3
"""Generate clearly synthetic shopping recordings and a geometric reference plate.

The recordings illustrate presentation mechanics. They do not run a model, query
real products, or measure inference performance.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw

from render_demo import ffmpeg_binary, font

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT, FPS = 576, 624, 12
INK, GRAY, LINE = '#252525', '#757C7B', '#E3E8E7'
ORANGE, APP = '#F15A29', '#F7F9F8'
PRODUCTS = [
    ('Sunburst tee', '$48', '#26292B', '#F1B14B', 'sun'),
    ('Mountain wolf tee', '$62', '#313A40', '#B9D2CB', 'mountain'),
    ('Stargazer tee', '$54', '#E1D7BF', '#6A5489', 'stars'),
    ('Wildflower tee', '$42', '#DBC3B1', '#A34748', 'flowers'),
    ('Solarwave tee', '$57', '#252932', '#E58361', 'waves'),
    ('Desert night tee', '$49', '#4C4141', '#EEC890', 'desert'),
]


def label(draw, text, xy, size=17, fill=INK, family='manrope-600.ttf'):
    draw.text(xy, text, font=font(family, size), fill=fill)


def wrapped(draw, text, xy, width, size=17, fill=INK, lines=10, family='manrope-600.ttf'):
    face = font(family, size)
    out, current = [], ''
    for word in text.split():
        test = (current + ' ' + word).strip()
        if draw.textlength(test, font=face) <= width:
            current = test
        else:
            out.append(current)
            current = word
    if current:
        out.append(current)
    x, y = xy
    for line in out[:lines]:
        draw.text((x, y), line, font=face, fill=fill)
        y += int(size * 1.4)
    return y


def star_points(cx, cy, outer, inner, n=5):
    return [(cx + (outer if i % 2 == 0 else inner) * math.cos(-math.pi / 2 + i * math.pi / n),
             cy + (outer if i % 2 == 0 else inner) * math.sin(-math.pi / 2 + i * math.pi / n))
            for i in range(n * 2)]


def tee(canvas, box, item):
    """Code-native garment silhouette and geometric print, not a product photograph."""
    x, y, width, height = box
    name, price, body, print_color, pattern = PRODUCTS[item % len(PRODUCTS)]
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((x, y, x + width, y + height), radius=10, fill='#ECEFEB')
    mx, my, scale = x + width / 2, y + height / 2, min(width, height) * 0.88
    def pt(a, b):
        return (mx + (a - 0.5) * scale, my + (b - 0.48) * scale)
    outline = [pt(a, b) for a, b in [(0.31, .08), (.41, .025), (.59, .025), (.69, .08),
                                     (.95, .25), (.82, .43), (.72, .35), (.72, .94),
                                     (.28, .94), (.28, .35), (.18, .43), (.05, .25)]]
    d.polygon(outline, fill=body)
    d.ellipse((pt(.415, -.005), pt(.585, .13)), fill='#ECEFEB')
    cx, cy = pt(.5, .49)
    r, weight = scale * .145, max(1, round(scale * .012))
    if pattern == 'sun':
        d.ellipse((cx-r*.55, cy-r*.55, cx+r*.55, cy+r*.55), fill=print_color)
        for a in range(0, 360, 30):
            rad = math.radians(a)
            d.line((cx+math.cos(rad)*r*.75, cy+math.sin(rad)*r*.75,
                    cx+math.cos(rad)*r*1.15, cy+math.sin(rad)*r*1.15), fill=print_color, width=weight)
    elif pattern == 'mountain':
        d.line((cx-r, cy+r*.5, cx-r*.15, cy-r*.85, cx+r*.7, cy+r*.5), fill=print_color, width=weight)
        d.line((cx-r*.15, cy-r*.85, cx+r*.15, cy-r*.3, cx+r*.32, cy-r*.52), fill=print_color, width=weight)
        d.polygon([(cx-r*.45,cy-r*.1),(cx-r*.25,cy-r*.4),(cx,cy-r*.12),
                   (cx+r*.25,cy-r*.4),(cx+r*.4,cy+r*.1),(cx,cy+r*.7)], fill=print_color)
    elif pattern == 'stars':
        d.polygon(star_points(cx, cy, r, r*.4), fill=print_color)
        for a, b, s in [(-.8,-.7,.18),(.8,-.4,.14),(.65,.8,.16)]:
            d.ellipse((cx+a*r-s*r,cy+b*r-s*r,cx+a*r+s*r,cy+b*r+s*r), fill=print_color)
    elif pattern == 'flowers':
        for dx,dy in [(-.55,-.1),(.4,-.3),(0,.65)]:
            fx,fy=cx+dx*r,cy+dy*r
            for a in range(0,360,72):
                px,py=fx+math.cos(math.radians(a))*r*.3,fy+math.sin(math.radians(a))*r*.3
                d.ellipse((px-r*.22,py-r*.22,px+r*.22,py+r*.22),fill=print_color)
            d.ellipse((fx-r*.12,fy-r*.12,fx+r*.12,fy+r*.12),fill='#F6DEAA')
    elif pattern == 'waves':
        for offset in [-.55,-.05,.45]:
            points=[(cx-r+i*r/10,cy+offset*r+math.sin(i/3)*r*.18) for i in range(21)]
            d.line(points,fill=print_color,width=weight)
    else:
        d.ellipse((cx-r*.65,cy-r*.95,cx+r*.65,cy+r*.35),fill=print_color)
        d.polygon([(cx-r,cy+r*.55),(cx-r*.25,cy-r*.05),(cx+r*.55,cy+r*.55)],fill=body)
        d.line((cx-r,cy+r*.65,cx+r,cy+r*.65),fill=print_color,width=weight)


def chrome(canvas, side):
    d = ImageDraw.Draw(canvas)
    d.rectangle((0,0,WIDTH,HEIGHT),fill=APP)
    d.rectangle((0,0,WIDTH,31),fill='#EFF3F1')
    for i,color in enumerate(('#EB7670','#EBC15C','#88BFA1')):
        d.ellipse((10+i*11,12,16+i*11,18),fill=color)
    label(d,'SYNTHETIC SOURCE · illustrative products',(62,8),12,GRAY)
    d.line((0,31,WIDTH,31),fill=LINE,width=1)
    d.rectangle((0,32,38,HEIGHT),fill='#F0F4F2')
    for i in range(9):
        yy=60+i*36
        if i==0:
            d.rounded_rectangle((8,yy-3,30,yy+19),radius=6,fill='#FFE6DB')
        d.ellipse((13,yy+2,25,yy+14),outline=ORANGE if side=='left' and i==0 else '#9CA8A3',width=2)
    label(d,'Vintage finds',(54,47),20,INK,'manrope-700.ttf')
    label(d,'Demo workspace',(54,76),12,GRAY)
    d.line((48,100,568,100),fill=LINE,width=1)
    d.rounded_rectangle((50,574,562,614),radius=15,fill='white',outline=LINE,width=1)
    label(d,'+',(64,579),22,GRAY)
    label(d,'Message…',(96,584),16,GRAY,'instrument-sans-latin.woff2')
    d.ellipse((531,585,549,603),fill='#DFEAE6')
    d.polygon([(536,595),(540,590),(544,595)],fill='#65786F')


def user_bubble(d, text, top=126, width=328):
    left=WIDTH-20-width
    face=font('manrope-600.ttf',16)
    words=text.split();nlines=1;line=''
    for w in words:
        trial=(line+' '+w).strip()
        if d.textlength(trial,font=face)>width-26:nlines+=1;line=w
        else:line=trial
    height=22*nlines+20
    d.rounded_rectangle((left,top,left+width,top+height),radius=13,fill='#DCECE8')
    wrapped(d,text,(left+13,top+10),width-26,16,lines=nlines)
    return top+height


def waiting(canvas, side, elapsed):
    d=ImageDraw.Draw(canvas)
    bottom=user_bubble(d,'Find a few bold vintage tees. Men’s size large. The louder the better.',top=334)
    label(d,'I’ll look for a few distinctive options.',(59,bottom+22),16,INK)
    message=['Checking illustrative listings','Comparing styles and sizes','Looking through more options'][int(max(0,elapsed)//6)%3]
    dot='.'*(1+int(elapsed*2)%3)
    d.rounded_rectangle((61,157,379,197),radius=12,fill='white',outline=LINE)
    label(d,'Search vintage tees'+dot,(76,168),15,GRAY)
    label(d,message+dot,(60,bottom+53),13,GRAY)
    # An indeterminate activity mark, with no percentage or timing claim.
    for i in range(3):
        size=3+(1 if int(elapsed*3)%3==i else 0)
        d.ellipse((64+i*14-size,229-size,64+i*14+size,229+size),fill='#A2B0A8')


def grid_results(canvas, more=False, followup=False):
    d=ImageDraw.Draw(canvas)
    user_bubble(d,'Show me three more.' if more else 'Bold vintage tees, size large.',top=116)
    label(d,'Here are three illustrative finds:',(57,191),18,INK,'manrope-700.ttf')
    for j in range(3):
        item=j+(3 if more else 0)
        x=56+j*169
        d.rounded_rectangle((x,225,x+158,435),radius=12,fill='white',outline=LINE)
        tee(canvas,(x+8,233,142,143),item)
        wrapped(d,PRODUCTS[item][0],(x+10,386),140,14,lines=2,family='manrope-700.ttf')
        label(d,PRODUCTS[item][1],(x+10,412),16,ORANGE,'manrope-700.ttf')
    wrapped(d,'Illustrative prices and artwork only. Open a card to inspect its design.',(58,460),486,15,GRAY,lines=3)
    if followup:
        # A short typing scene, then the second set of results replaces the list.
        d.rounded_rectangle((185,516,553,557),radius=12,fill='#DCECE8')
        label(d,'Show me three more.',(200,526),16,INK)


def detail(canvas, selected, more=False):
    d=ImageDraw.Draw(canvas)
    label(d,'Three more illustrative picks' if more else 'Three illustrative picks',(54,119),17,INK,'manrope-700.ttf')
    for j in range(3):
        item=j+(3 if more else 0);yy=160+j*115
        fill='#FFF1E9' if item==selected else 'white'
        d.rounded_rectangle((52,yy,307,yy+103),radius=11,fill=fill,outline='#F1BEA6' if item==selected else LINE)
        tee(canvas,(60,yy+9,78,84),item)
        wrapped(d,PRODUCTS[item][0],(149,yy+16),144,15,lines=2,family='manrope-700.ttf')
        label(d,PRODUCTS[item][1],(149,yy+66),17,ORANGE,'manrope-700.ttf')
    d.rounded_rectangle((320,109,568,563),radius=11,fill='white',outline=LINE)
    label(d,'Product detail',(335,121),14,GRAY)
    label(d,'×',(542,119),19,GRAY)
    tee(canvas,(332,155,224,221),selected)
    y=wrapped(d,PRODUCTS[selected][0],(335,392),210,21,lines=2,family='manrope-700.ttf')
    label(d,PRODUCTS[selected][1],(335,y+7),22,ORANGE,'manrope-700.ttf')
    label(d,'Size L · illustrative listing',(335,y+42),13,GRAY)
    d.rounded_rectangle((335,510,553,544),radius=9,fill='#324A42')
    label(d,'View item',(404,517),15,'white','manrope-700.ttf')


def frame(side, timestamp):
    elapsed=max(0,timestamp-.5)
    canvas=Image.new('RGB',(WIDTH,HEIGHT),APP)
    chrome(canvas,side)
    if timestamp<.5:
        d=ImageDraw.Draw(canvas)
        label(d,'Ready for your request',(126,267),22,GRAY,'manrope-700.ttf')
    elif side=='right':
        if elapsed<20:waiting(canvas,side,elapsed)
        else:grid_results(canvas)
    elif elapsed<4:
        waiting(canvas,side,elapsed)
    elif elapsed<4.6:
        grid_results(canvas)
    elif elapsed<6:
        detail(canvas,0)
    elif elapsed<8:
        detail(canvas,1)
    elif elapsed<9:
        grid_results(canvas,followup=True)
    elif elapsed<10:
        grid_results(canvas,more=True)
    else:
        detail(canvas,5,more=True)
    return canvas


def make_videos():
    ffmpeg=ffmpeg_binary()
    media=ROOT/'examples'/'media';media.mkdir(parents=True,exist_ok=True)
    for side,duration in [('left',13.5),('right',22)]:
        path=media/f'story-{side}.mp4'
        cmd=[ffmpeg,'-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{WIDTH}x{HEIGHT}',
             '-r',str(FPS),'-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','18',
             '-pix_fmt','yuv420p','-movflags','+faststart',str(path)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        try:
            for i in range(round(duration*FPS)):
                proc.stdin.write(frame(side,i/FPS).tobytes())
            proc.stdin.close()
            if proc.wait():raise RuntimeError(f'Encoding failed: {path.name}')
        except Exception:
            proc.terminate();proc.wait();raise
        print(f'{path.name}: {WIDTH}×{HEIGHT}, {duration:g}s, {FPS}fps, silent')


def make_background(light=False):
    out=ROOT/'assets'/'backgrounds';out.mkdir(parents=True,exist_ok=True)
    width,height=3840,2160
    base='#F5F5F0' if light else '#F15A29'
    dots='#EBDCD5' if light else '#F9C7B6'
    canvas=Image.new('RGB',(width,height),base);d=ImageDraw.Draw(canvas)
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
         '<title>Recreated halftone reference style</title>',
         '<desc>Geometric recreation of the reference comparison layout halftone. Not an original design-tool export.</desc>',
         f'<rect width="{width}" height="{height}" fill="{base}"/>']
    spacing=18
    for y in range(0,height+spacing,spacing):
        for x in range(0,width+spacing,spacing):
            upper=math.hypot((width-x)/1850,y/1340)
            lower=math.hypot(x/1850,(height-y)/1340)
            strength=max(0,1-min(upper,lower))
            radius=(4.5 if light else 6.5)*strength**.72
            if radius<.65:continue
            d.ellipse((x-radius,y-radius,x+radius,y+radius),fill=dots)
            svg.append(f'<circle cx="{x}" cy="{y}" r="{radius:.3f}" fill="{dots}"/>')
    stem='reference-light-halftone' if light else 'reference-orange-halftone'
    canvas.save(out/f'{stem}.png',optimize=True)
    (out/f'{stem}.svg').write_text('\n'.join(svg+['</svg>'])+'\n')
    provenance={'status':'recreated_geometric_background','original_design_export':False,
                'source_reference':'a Cerebras side-by-side comparison layout',
                'dimensions':[width,height],'base_color':base,'formats':['svg','png'],
                'generator':'scripts/make_story_example.py',
                'notes':'The reference uses an orange field with pale halftone corners. This is newly drawn geometry, not a plate extracted from or inpainted over any video. Source clips generated by this script are synthetic and contain no inference measurements.'}
    (out/f'{stem}-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(f'{stem}: {width}×{height}, SVG master and PNG')


def main():
    make_background()
    make_background(light=True)
    make_videos()


if __name__=='__main__':
    main()
