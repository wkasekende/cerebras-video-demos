#!/usr/bin/env python3
"""The golden tile ground's lab: components/agent/bloom.js (AgBloom.TILE) drawn live beside the texture the owner supplied, zoomed to the video's full width, with a difference image
and a slider for every number. A DRAFT of a new theme's ground: the shapes were fitted to the texture, the tile lines and discs were measured off it.

    python3 artifact/agent_tile.py
      -> out/agent-tile.artifact.html   the page body for the Artifact tool
      -> out/agent-tile.page.html       the same page as a local, standalone HTML file

The reference is a reference video (1254 x 1254) scaled to 1920 x 1920 and cropped to the middle 1080 rows, so a 1920 x 1080 frame
shows the texture as it would sit behind a window.
"""
import base64, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, HERE)
import build  # noqa: E402
import agent_video4 as V4  # noqa: E402  (the lab's page style)

REF = os.path.join(ROOT, "references", "agent-gold-tile", "frames", "zoomed-1920x1080.jpg")
BLOOM = open(os.path.join(ROOT, "components", "agent", "bloom.js"), encoding="utf-8").read()


def small():
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", REF, "-vf", "scale=960:540", "-q:v", "4", "-f", "image2pipe", "-vcodec", "mjpeg", "-"], check=True, capture_output=True).stdout
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode()


JS = r"""
<script>
(function(){
  var P=JSON.parse(JSON.stringify(AgBloom.TILE)),W=960,H=540;
  var cv=document.getElementById('b-canvas'),df=document.getElementById('b-diff'),ref=document.getElementById('b-ref'),err=document.getElementById('b-err'),out=document.getElementById('b-out'),box=document.getElementById('b-sl');
  cv.width=df.width=W;cv.height=df.height=H;var refData=null;
  function loadRef(){function go(){var c=document.createElement('canvas');c.width=W;c.height=H;var x=c.getContext('2d');x.drawImage(ref,0,0,W,H);refData=x.getImageData(0,0,W,H).data;redraw()}
    if(ref.complete&&ref.naturalWidth)go();else ref.onload=go}
  function redraw(){
    AgBloom.draw(cv,P);
    if(!refData)return;
    var a=cv.getContext('2d').getImageData(0,0,W,H).data,dctx=df.getContext('2d'),o=dctx.createImageData(W,H),d=o.data,i,s=0,n=W*H,v;
    for(i=0;i<n;i++){var j=i*4;v=(Math.abs(a[j]-refData[j])+Math.abs(a[j+1]-refData[j+1])+Math.abs(a[j+2]-refData[j+2]))/3;s+=v;v=Math.min(255,v*5);d[j]=d[j+1]=d[j+2]=v;d[j+3]=255}
    dctx.putImageData(o,0,0);
    err.innerHTML='mean error <b>'+(s/n).toFixed(2)+'</b> / 255 (the texture\'s own fine grain alone is about 3)';
    out.textContent=JSON.stringify(P);
  }
  var later=function(){clearTimeout(later.t);later.t=setTimeout(redraw,60)};
  function build(){
    var h='';
    function grp(t){h+='<div class="grp">'+t+'</div>'}
    var defs=[];
    function sl(id,label,min,max,step,get,set){defs.push({id:id,get:get,set:set});h+='<div class="sl"><label for="'+id+'">'+label+'</label><output id="'+id+'-o"></output><input id="'+id+'" type="range" min="'+min+'" max="'+max+'" step="'+step+'"></div>'}
    function col(id,label,get,set){defs.push({id:id,get:get,set:set,color:1});h+='<div class="sl"><label for="'+id+'">'+label+'</label><output id="'+id+'-o"></output><input id="'+id+'" type="color"></div>'}
    grp('Base');col('bc','Base colour',function(){return P.base},function(v){P.base=v});
    P.glows.forEach(function(g,i){grp(['The gold glow (the bright middle)','The orange glow (left of it)','The olive glow (right side)'][i]||('Glow '+(i+1)));
      ['x','y'].forEach(function(f){sl('g'+i+f,f.toUpperCase(),-0.3,1.3,0.005,function(){return g[f]},function(v){g[f]=v})});
      ['rx','ry'].forEach(function(f){sl('g'+i+f,'Reach '+f,0.05,1.5,0.005,function(){return g[f]},function(v){g[f]=v})});
      sl('g'+i+'a','Strength at the centre',0,1,0.01,function(){return g.a},function(v){g.a=v});sl('g'+i+'m','Strength half way out',0,1,0.01,function(){return g.mid},function(v){g.mid=v});
      col('g'+i+'c','Colour',function(){return g.c},function(v){g.c=v})});
    grp('The dark brown on the left (a drawn ellipse, then blurred)');
    ['x','y','rx','ry'].forEach(function(f){sl('bb'+f,'Blob '+f,f.length>1?0.05:-0.4,f.length>1?1.5:1.3,0.005,function(){return P.blob[f]},function(v){P.blob[f]=v})});
    sl('bba','Strength',0,1,0.01,function(){return P.blob.a},function(v){P.blob.a=v});sl('bbb','Blur (px at 1920)',0,400,1,function(){return P.blob.blur},function(v){P.blob.blur=v});col('bbc','Colour',function(){return P.blob.c},function(v){P.blob.c=v});
    grp('Its halo');sl('hs','Size (x the blob)',1,1.8,0.01,function(){return P.halo.scale},function(v){P.halo.scale=v});sl('ha','Strength',0,1,0.01,function(){return P.halo.a},function(v){P.halo.a=v});sl('hb','Blur',0,400,1,function(){return P.halo.blur},function(v){P.halo.blur=v});col('hc','Colour',function(){return P.halo.c},function(v){P.halo.c=v});
    grp('The vignette (edges darken)');sl('va','Strength',0,1,0.01,function(){return P.vignette.a},function(v){P.vignette.a=v});sl('vp','Falloff (higher = tighter to the edge)',0.5,5,0.05,function(){return P.vignette.power},function(v){P.vignette.power=v});col('vc','Colour',function(){return P.vignette.c},function(v){P.vignette.c=v});
    grp('The tiles: hairlines and a disc at each crossing');
    sl('tpx','Tile width (px at 1920)',60,320,0.1,function(){return P.tiles.pitchX},function(v){P.tiles.pitchX=v});sl('tpy','Tile height',60,420,0.1,function(){return P.tiles.pitchY},function(v){P.tiles.pitchY=v});
    sl('tox','Offset x',0,320,0.5,function(){return P.tiles.offX},function(v){P.tiles.offX=v});sl('toy','Offset y',0,420,0.5,function(){return P.tiles.offY},function(v){P.tiles.offY=v});
    sl('tl','Line width',0.5,8,0.05,function(){return P.tiles.line},function(v){P.tiles.line=v});sl('td','Disc radius',0,24,0.1,function(){return P.tiles.dot},function(v){P.tiles.dot=v});
    col('tc','Colour (lines and discs are one solid colour)',function(){return P.tiles.c},function(v){P.tiles.c=v});sl('tq','Opacity (the whole layer, so a line and a disc never darken twice)',0,1,0.01,function(){return P.tiles.opacity},function(v){P.tiles.opacity=v});
    grp('The speckle (very light, following the glows so it shimmers; the preview here is half size)');
    sl('sz','Speck size',0.5,4,0.05,function(){return P.speckle.size},function(v){P.speckle.size=v});sl('sv','Variety (big specks)',0,1,0.01,function(){return P.speckle.variety},function(v){P.speckle.variety=v});
    sl('sc','Big-speck scale',1,12,0.1,function(){return P.speckle.coarse},function(v){P.speckle.coarse=v});sl('sk','Edge: soft to hard',1,30,0.5,function(){return P.speckle.contrast},function(v){P.speckle.contrast=v});
    sl('sb','Speckle blur (px)',0,6,0.1,function(){return P.speckle.blur},function(v){P.speckle.blur=v});
    P.speckle.layers.forEach(function(L,i){grp('Speckle: '+L.name+(L.glow!=null?' (follows glow '+(L.glow+1)+')':' (follows the dark ellipse)'));
      sl('l'+i+'g','Density (x the map)',0,2,0.01,function(){return L.gain},function(v){L.gain=v});sl('l'+i+'a','Strength',0,1,0.01,function(){return L.amount},function(v){L.amount=v});sl('l'+i+'k','Push (how much lighter or darker a speck is)',0,3,0.05,function(){return L.k},function(v){L.k=v});
      if(L.lum){sl('l'+i+'lo','Lightness it starts at (0 dark - 1 light)',0,1,0.01,function(){return L.lum.lo},function(v){L.lum.lo=v});sl('l'+i+'hi','Lightness it is full at',0,1,0.01,function(){return L.lum.hi},function(v){L.lum.hi=v});
        sl('l'+i+'pw','Ramp (higher = only the extremes)',0.3,4,0.05,function(){return L.lum.power},function(v){L.lum.power=v});sl('l'+i+'iv','Strongest in the dark (1) or the light (0)',0,1,1,function(){return L.lum.invert},function(v){L.lum.invert=v})}});
    grp('Texture');sl('gr','Grain (the paper-like fine texture)',0,0.2,0.005,function(){return P.grain},function(v){P.grain=v});sl('dt','Dither (smooths the soft shapes)',0,6,0.1,function(){return P.dither},function(v){P.dither=v});
    box.innerHTML=h;
    defs.forEach(function(d){var i=document.getElementById(d.id),o=document.getElementById(d.id+'-o');
      function show(){o.textContent=d.color?d.get():(+d.get()).toFixed(3)}
      i.value=d.get();show();
      i.addEventListener('input',function(){d.set(d.color?i.value:+i.value);show();later()})})}
  document.getElementById('b-reset').addEventListener('click',function(){P=JSON.parse(JSON.stringify(AgBloom.TILE));build();redraw()});
  document.getElementById('b-copy').addEventListener('click',function(){var b=this,t=JSON.stringify(P);function ok(m){b.textContent=m;setTimeout(function(){b.textContent='Copy parameters'},1500)}
    try{navigator.clipboard.writeText(t).then(function(){ok('Copied')},function(){ok('Select the text below')})}catch(e){ok('Select the text below')}});
  build();loadRef();
})();
</script>
"""


def main():
    body = f'''<meta name="claude:viewport-fit-sides" content="cover">
<title>Agent Tile Ground</title>
<style>{build.fontface()}{V4.CSS}</style>
<div class="v4">
<h1>Golden tile: the ground</h1>
<p class="lede">A draft of a new theme's background, from the golden brown tiled texture you supplied, zoomed to the full width of a 1920 x 1080 frame (the texture is square, so the middle 1080 rows show). It is the same drawn-shape machinery as the bloom ground: a gold glow, an orange one and an olive one, a dark brown ellipse on the left, a vignette, then the tiled floor: solid hairlines 160 px wide by 224.9 px tall with a solid disc of the same colour at every crossing, laid over with one opacity so they blend into the ground, then a very light speckle that follows the glows and the ground's own lightness (shimmer strongest where it is brightest, dark flecks strongest where it is darkest), then fine grain. The shapes were fitted to the texture; the tile pitch and offsets were measured off it. Every number has a slider; send me the parameters when it looks right.</p>
<div class="trio">
<figure><figcaption>The texture, zoomed</figcaption><div class="pic"><img id="b-ref" src="{small()}" alt="the texture, zoomed to 1920 wide"></div></figure>
<figure><figcaption>Rebuilt</figcaption><div class="pic"><canvas id="b-canvas"></canvas></div></figure>
<figure><figcaption>Difference x5</figcaption><div class="pic"><canvas id="b-diff"></canvas></div></figure>
</div>
<p class="err" id="b-err" aria-live="polite"></p>
<div class="row"><button id="b-reset" type="button">Reset to the fitted values</button><button id="b-copy" type="button">Copy parameters</button></div>
<pre class="out" id="b-out"></pre>
<div class="lab" id="b-sl"></div>
</div>
<script>{BLOOM}</script>
{JS}
'''
    out = os.path.join(ROOT, "out")
    os.makedirs(out, exist_ok=True)
    pth = os.path.join(out, "agent-tile.artifact.html")
    open(pth, "w", encoding="utf-8").write(body)
    open(os.path.join(out, "agent-tile.page.html"), "w", encoding="utf-8").write(
        "<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'></head><body>" + body + "</body></html>")
    print(pth, len(body) // 1024, "KB")


if __name__ == "__main__":
    main()
