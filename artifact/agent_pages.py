#!/usr/bin/env python3
"""The agent PAGES: every full 1920 x 1080 composition the two reference videos show, rebuilt from the shared components and set beside the real frame.

    python3 artifact/agent_pages.py
      -> out/agent-pages.artifact.html   the page body for the Artifact tool
      -> out/agent-pages.page.html       the same page as a local, standalone HTML file

Each page is the video's frame and the rebuild in the chosen theme (ember, paper or glow; one switch for the whole page), at the same size, so a ground, a
window, a composer and a claim can be judged where they actually sit. The pieces are artifact/agent_components.py's builders, nested at the crop box
where the video has them, on ONE full-frame ground drawn behind everything (NEST makes a component transparent and ground-less).
"""
import html, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "tools"))
import agent_components as A  # noqa: E402
import build  # noqa: E402

W, H = 1920, 1080


def place(x, y, body):
    return f'<div style="position:absolute;left:{x}px;top:{y}px">{body}</div>'


def shell(x, y, w, h, radius, body):
    """the app window: its own surface and shadow; children are placed in the window's own coordinates"""
    return f'<div class="ag-window" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;border-radius:{radius}px">{body}</div>'


def page(theme, inner, kind=None):
    glow = None
    if kind in (None, "typing"):   # every page that shows the gradient ground uses the clustered ground preset (ground.js GLOW.typing); the claim and lockup keep their own dark grounds
        kind, glow = None, "typing"
    """one full-frame stage: the ground behind everything, then the nested components"""
    A.NEST = False; A.FRAME_OFF = (0, 0)
    dark = kind in ("claim", "lockup")
    ground = A.gnd("dim" if dark else "bright", glow)
    A.NEST = True
    try:
        body = inner(theme)
    finally:
        A.NEST = False
    k = f' data-kind="{kind}"' if kind else ""
    bg = "background:var(--ground-dim);" if dark else ""
    return f'<div class="ag{" ag-dim" if dark else ""}" data-theme="{theme}" data-partner="white"{k} style="width:{W}px;height:{H}px;{bg}">{ground}{body}</div>'


def caption(t):
    return place(700, 1000, A.c2_caption(t))


# ── the pages of the second video (a light window on a gradient: Muse Spark Open) ───────────────────────────────
def v2_typing(t):
    return place(330, 410, A.c2_composer(t))


def v2_welcome(t):
    return place(196, 62, A.c2_welcome(t)) + caption(t)


def v2_window(t, content):
    return shell(196, 62, 1528, 900, 28, A.titlebar(True, "Muse Spark Open", short=True) + content) + caption(t)


def v2_turn(t):
    return v2_window(t, place(560 - 196, 150 - 62, A.c2_turn(t)) + place(560 - 196, 820 - 62, A.c2_docked(t, "stop")))


def v2_answer(t):
    return v2_window(t, place(560 - 196, 215 - 62, A.c2_answer(t)) + place(560 - 196, 820 - 62, A.c2_docked(t)))


def v2_card(t):
    return place(240, 80, A.c2_card(t)) + caption(t)


def v2_claim(t):
    return place(0, 400, A.c2_claim(t))


def v2_lockup(t):
    return place(400, 400, A.c2_lockup(t))


# ── the pages of the first video (a dark window with a browser pane: Kimi K3.1 Pro) ──────────────────────────────
def v1_typing(t):
    return place(150, 340, A.c_composer_hero(t))


def v1_welcome(t):
    return place(156, 44, A.c_welcome(t))


BUBBLE = ('<div class="ag-bubble" style="left:263px;top:31px;width:488px;padding:19px 20px;font-size:15.5px;border-radius:24px">Go to Walmart and compare the Ninja AF140 and AF180 air fryers. '
          'Compare their price, capacity, cooking modes, and cleaning features. Recommend which is better for a household of four and explain why. Check out with the best one.</div>')


def v1_window(t, left, right):
    browser = place(965 - 156, 44 - 44, A.c_browser(t)) + '<div style="position:absolute;left:809px;top:200px;width:799px;height:792px;background:var(--page)"></div>' + right
    # the title bar's icons belong to the CHAT half (the pane has its own tab strip) and a 2 px hairline divides the halves (read off f033: x 964-965, about #1f2121 on #151716)
    bar = '<div style="position:absolute;left:0;top:0;width:810px;height:76px">' + A.titlebar() + '</div>'
    divider = '<div style="position:absolute;left:808px;top:0;width:2px;height:992px;background:rgba(255,255,255,.075)"></div>'
    return shell(156, 44, 1608, 992, 20, bar + divider + left + browser)


def v1_working(t):
    left = '<div style="position:absolute;left:0;top:80px;width:810px;height:300px">' + BUBBLE.replace("left:263px;top:31px", "left:263px;top:31px") + '</div>' + place(180 - 156, 330 - 44 + 40, A.c_tool(t)) + place(0, 880 - 44, A.c_composer_docked(t))
    return v1_window(t, left, "")


def v1_answer(t):
    left = place(230 - 156, 120 - 44, A.c_answer(t)) + place(0, 880 - 44, A.c_composer_docked(t))
    return v1_window(t, left, place(985 - 156, 330 - 44, A.c_redaction(t)))


def v1_claim(t):
    return place(0, 330, A.c_claim(t))


def v1_lockup(t):
    return place(400, 400, A.c_lockup(t))


# ── the pages of the third video (a light window on a flat vermilion halftone: Kimi K3.1 Pro buys a monitor) ───────
def v3_typing(t):
    return place(60, 320, A.c3_composer(t))


def v3_welcome(t):
    return place(152, 36, A.c3_welcome(t))


def v3_window(t, content):
    return shell(152, 36, 1615, 1006, 24, content)


def v3_turn(t):
    return v3_window(t, A.titlebar(True, "Kimi K3.1 Pro", short=True) + place(1330 - 152, 50 - 36, A.c3_timer(t)) + place(560 - 152, 140 - 36, A.c3_turn(t))
                     + place(520 - 152, 890 - 36, A.c3_docked(t)))


def v3_answer(t):
    toolcard = ('<div class="ag-tool" style="left:%dpx;top:%dpx;width:358px;height:316px"><div class="ag-shot" style="height:268px;overflow:hidden"><div style="transform:scale(.447);transform-origin:0 0;width:801px">%s</div></div>'
                '<div class="ag-cap"><span style="color:var(--ink-2)">%s</span><span>Store</span></div></div>') % (242 - 152, 135 - 36, A.c3_pane(t), A.ic("globe", 20, 1.6))
    left = ('<div style="position:absolute;left:0;top:0;width:814px;height:76px">' + A.titlebar(True, "Kimi K3.1 Pro") + '</div>' + toolcard
            + place(232 - 152, 460 - 36, A.c3_answer(t)) + place(172 - 152 - 8, 890 - 36, A.c3_docked(t, "done")))
    divider = '<div style="position:absolute;left:813px;top:0;width:2px;height:1006px;background:rgba(0,0,0,.065)"></div>'   # read off f047: x 965-966, about #edefef on #fbfdfd
    return v3_window(t, left + divider + place(966 - 152, 0, A.c3_pane(t)) + place(1330 - 152, 50 - 36, A.c3_timer(t, "11.5s")) + place(150 - 152, 440 - 36, A.c3_confetti(t)))


def v3_claim(t):
    return place(0, 380, A.c3_claim(t))


def v3_lockup(t):
    return place(400, 400, A.c3_lockup(t))


# ── the pages of the fourth video (the first video's dark window and browser pane, on the bloom ground: Kimi 3.1 Pro orders a sandwich) ───────────────
def v4_typing(t):
    return place(150, 400, A.c4_composer(t))


def v4_welcome(t):
    return place(156, 44, A.c4_welcome(t))


def v4_window(t, state, kind, docked):
    # the title bar's icons belong to the CHAT half (the pane has its own tab strip), and a 2 px hairline (about #222424 on #151716) divides the two halves
    bar = '<div style="position:absolute;left:0;top:0;width:810px;height:76px">' + A.titlebar() + '</div>'
    divider = '<div style="position:absolute;left:810px;top:0;width:2px;height:992px;background:rgba(255,255,255,.075)"></div>'
    return shell(156, 44, 1608, 992, 20, bar + divider + place(0, 0, A.c4_turn(t, state, False)) + place(966 - 156, 0, A.c4_pane(t, kind)) + place(165 - 156, 886 - 44, A.c4_docked(t, docked)))


def v4_working(t):
    return v4_window(t, "working", "home", "stop")


def v4_question(t):
    return v4_window(t, "question", "modal", "stop")


def v4_answer(t):
    return v4_window(t, "answer", "confirm", "done")


def v4_claim(t):
    return place(0, 330, A.c_claim(t))


def v4_lockup(t):
    return place(400, 400, A.c_lockup(t))


# (id, title, what it is, video, frame, builder, kind)
PAGES = [
 ("v2-typing", "Typing", "the prompt typed into the composer, centred on the ground, before the window exists", 2, "f009", v2_typing, "typing"),
 ("v2-welcome", "Welcome", "the window at rest: the mark, the question, the composer holding the prompt", 2, "f015", v2_welcome, None),
 ("v2-turn", "A turn in progress", "the user's bubble, the assistant's interim message, a tool line and the live meter, with the stop button in the composer", 2, "f019", v2_turn, None),
 ("v2-answer", "The answer", "the 'Worked for' line, the markdown answer card, its footer, and the composer with the rate chip", 2, "f025", v2_answer, None),
 ("v2-card", "The integration card", "the window blurred behind a white card", 2, "f051", v2_card, None),
 ("v2-claim", "The claim", "the model, the number, the footnote, on the near-black ground", 2, "f059", v2_claim, "claim"),
 ("v2-lockup", "Powered by Cerebras", "the closing lockup", 2, "f062", v2_lockup, "lockup"),
 ("v1-typing", "Typing", "the first video's prompt in the dark composer on the grid", 1, "f013", v1_typing, None),
 ("v1-welcome", "Welcome", "the dark window at rest", 1, "f027", v1_welcome, None),
 ("v1-working", "Working in a browser", "the chat on the left, the live tool card, the browser pane on the right", 1, "f033", v1_working, None),
 ("v1-answer", "The answer", "the table answer on the left, the order page on the right", 1, "f055", v1_answer, None),
 ("v1-claim", "The claim", "Kimi K3.1 Pro, the number, the footnote", 1, "f065", v1_claim, "claim"),
 ("v1-lockup", "House and partner", "the closing lockup", 1, "f078", v1_lockup, "lockup"),
 ("v3-typing", "Typing", "the prompt typed into a wide pill composer, centred on the vermilion halftone, before the window exists", 3, "f015", v3_typing, "typing"),
 ("v3-welcome", "Welcome", "the window at rest on the halftone: the mark, the question, the composer holding the prompt", 3, "f019", v3_welcome, None),
 ("v3-turn", "A turn in progress", "the timer pill counting, the user's bubble, 'Preparing this turn', and the stop button in the docked composer", 3, "f021", v3_turn, None),
 ("v3-answer", "The answer", "the order card with confetti, its footer, the docked composer, and the browser pane on the thank-you page", 3, "f047", v3_answer, None),
 ("v3-claim", "The claim", "Kimi K3.1 Pro, the number, the footnote, on the warm halftone", 3, "f055", v3_claim, "claim"),
 ("v3-lockup", "Powered by Cerebras", "the house and partner logos with a hairline, on the warm halftone", 3, "f065", v3_lockup, "lockup"),
 ("v4-typing", "Typing", "the prompt typed into the dark composer on the bloom ground, before the window exists", 4, "f015", v4_typing, "typing"),
 ("v4-welcome", "Welcome", "the window at rest: the mark, the question, the composer holding the one-line prompt", 4, "f019", v4_welcome, None),
 ("v4-working", "Working", "the first turn: the bubble, 'Using Browser' with a live thumbnail, the meter, and the browser pane on the home page", 4, "f025", v4_working, None),
 ("v4-question", "The assistant asks", "the question card with bold options, the user's one-word reply, the next tool card, and the pane on an item's option sheet", 4, "f045", v4_question, None),
 ("v4-answer", "The answer", "'Worked for 9 seconds', the thumbnail, the order answer card and footers, and the pane on the confirmation page", 4, "f067", v4_answer, None),
 ("v4-claim", "The claim", "Kimi 3.1 Pro, the number, the footnote, on the dim bloom ground", 4, "f073", v4_claim, "claim"),
 ("v4-lockup", "Powered by Cerebras", "the house and partner logos with a hairline, white on the dim bloom ground", 4, "f085", v4_lockup, "lockup"),
]
THEMES = [("glow", "Glow (video 2's)"), ("halftone", "Halftone (video 3's)"), ("bloom", "Bloom (video 4's)"), ("tile", "Tile (the gold ground)"), ("ember", "Ember (video 1's)"), ("paper", "Paper (the original's)")]

CSS = """
.pg .ctl{position:sticky;top:0;z-index:30;background:var(--bg);padding:10px 0;border-bottom:1px solid var(--rule);display:flex;gap:18px;flex-wrap:wrap;align-items:center}
.pg .ctl label{display:flex;align-items:center;gap:7px;font-size:14px;cursor:pointer}.pg .ctl input{accent-color:#e25124;width:16px;height:16px}
.pg .ctl .seg{display:flex;gap:6px}.pg .ctl button{font:inherit;font-size:13px;padding:7px 13px;border-radius:999px;border:1px solid var(--rule);background:var(--panel);color:var(--fg);cursor:pointer}
.pg .ctl button.on{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.pg .scene{margin-top:34px;border-top:1px solid var(--rule);padding-top:16px}.pg .scene h3{margin:0;font-size:18px;font-weight:600;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.pg .scene .why{margin:4px 0 12px;color:var(--muted);font-size:14px;max-width:80ch}
.pg .duo{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.pg.stack .duo{grid-template-columns:minmax(0,1fr)}
@media (max-width:760px){.pg .duo{grid-template-columns:minmax(0,1fr)}}
.pg .cell{min-width:0}.pg .cap{font-family:'Sometype Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:0 0 6px}
.pg .lab-top{top:56px}   /* below the page's own pinned controls */
.pg h2.vid{font-size:20px;font-weight:600;margin:46px 0 0;letter-spacing:-.01em}
"""

LAB_JS = """<script>
(function(){
  var DEFS=[['angle','ROTATE the gradient colours (deg)',90,180,1],['clusterAngle','ROTATE the speckle clusters (deg; start equal to the gradient)',90,180,1],['shift','MOVE the middle along the axis (% of the diagonal; corners stay full)',-30,30,1],['liteAmount','Light speckle: strength',0,1,.01],['liteMid','Light: density through the middle',0,1,.01],['liteEdgeA','Light: maximum at the top-left',0,1,.01],['liteEdgeB','Light: maximum at the bottom-right',0,1,.01],
    ['darkAmount','Dark speckle: strength',0,1,.01],['darkDensity','Dark: density through the middle',0,1,.01],['darkEdgeA','Dark: maximum at the top-left',0,1,.01],['darkEdgeB','Dark: maximum at the bottom-right',0,1,.01],
    ['redAmount','Red speckle: strength',0,1,.01],['clusterMid','Red: density through the middle',0,1,.01],['clusterEdge','Red: maximum at the top-left',0,1,.01],['clusterEdgeB','Red: maximum at the bottom-right',0,1,.01],
    ['clusterFollow','Follow the gradient: the clusters cross-fade where the colours do (1), or fade over their own reach (0)',0,1,1],['from','Gradient: the light colour holds to (% of the diagonal)',0,100,1],['to','Gradient: the dark colour is reached at (%)',0,100,1],['clusterReach','Own reach, when not following (% of the diagonal)',5,100,1],['clusterGamma','Falloff: 1 is linear, higher is tighter',.3,4,.1],['contrast','Edge: soft to hard',1,30,.5],['blur','Blur (px)',0,10,.25],['seed','Seed: the frozen frame',0,99,1]];
  var G=window.AgGround,P=Object.assign({},G.GLOW.typing),g=document.getElementById('tl-ground'),box=document.getElementById('tl-sliders'),out=document.getElementById('tl-params'),busy=document.getElementById('tl-busy');
  function fmt(v,step){return step<1?(+v).toFixed(step<.1?2:1):String(v)}
  function show(){out.textContent=JSON.stringify(P).replace(/,/g,', ').replace(/"/g,'')}
  var tm=0;function later(){clearTimeout(tm);busy.hidden=false;tm=setTimeout(function(){G.applyGlow(g,P);var w=setInterval(function(){if(G.pending===0){clearInterval(w);busy.hidden=true}},60)},180);show()}
  function sliders(){box.innerHTML='';DEFS.forEach(function(d){var k=d[0],w=document.createElement('div');w.className='sl';
    w.innerHTML='<label for="tl-'+k+'">'+d[1]+'</label><output></output><input id="tl-'+k+'" type="range" min="'+d[2]+'" max="'+d[3]+'" step="'+d[4]+'">';
    box.appendChild(w);var i=w.querySelector('input'),o=w.querySelector('output');var cur=P[k]==null?(k=='clusterAngle'?P.angle:P.clusterEdge):P[k];i.value=cur;o.textContent=fmt(cur,d[4]);
    i.addEventListener('input',function(){P[k]=+i.value;o.textContent=fmt(i.value,d[4]);later()})})}
  document.getElementById('tl-reset').addEventListener('click',function(){P=Object.assign({},G.GLOW.typing);sliders();later()});
  document.getElementById('tl-copy').addEventListener('click',function(){var b=this,t=JSON.stringify(P);function done(m){b.textContent=m;setTimeout(function(){b.textContent='Copy parameters'},1600)}
    function pick(){var r=document.createRange();r.selectNodeContents(out);var s=getSelection();s.removeAllRanges();s.addRange(r);done('Selected: copy it')}
    try{navigator.clipboard.writeText(t).then(function(){done('Copied')},pick)}catch(e){pick()}});
  sliders();show();
})();
</script>"""

JS = """<script>
(function(){
  var root=document.querySelector('.pg');
  function fit(){document.querySelectorAll('.fit').forEach(function(f){var pw=f.parentNode.clientWidth;if(!pw)return;var w=+f.dataset.w,h=+f.dataset.h,s=Math.min(1,pw/w);
    f.style.height=(h*s)+'px';f.style.width=(w*s)+'px';var i=f.firstElementChild;i.style.width=w+'px';i.style.height=h+'px';i.style.transform='scale('+s+')';})}
  function theme(t){document.querySelectorAll('[data-pt]').forEach(function(e){e.hidden=e.dataset.pt!==t});
    document.querySelectorAll('[data-theme-btn]').forEach(function(b){b.classList.toggle('on',b.dataset.themeBtn===t)});fit()}
  document.querySelectorAll('[data-theme-btn]').forEach(function(b){b.addEventListener('click',function(){theme(b.dataset.themeBtn)})});
  document.getElementById('set-stack').addEventListener('change',function(){root.classList.toggle('stack',this.checked);fit()});
  var c=document.getElementById('set-partner');c.addEventListener('change',function(){document.querySelectorAll('.ag').forEach(function(el){if(c.checked)el.setAttribute('data-partner','white');else el.removeAttribute('data-partner')})});
  window.addEventListener('resize',fit);
  if(document.fonts&&document.fonts.ready)document.fonts.ready.then(fit);
  theme('glow');
})();
</script>"""


def main():
    cells = []
    for vid in (4, 3, 2, 1):
        cells.append(f'<h2 class="vid">{"Fourth video: a dark window on a blurred bloom (Kimi 3.1 Pro orders a sandwich)" if vid == 4 else "Third video: a light window on a vermilion halftone (Kimi K3.1 Pro buys a monitor)" if vid == 3 else "Second video: a light window on a gradient (Muse Spark Open)" if vid == 2 else "First video: a dark window with a browser pane (Kimi K3.1 Pro)"}</h2>')
        for pid, title, why, v, frame, fn, kind in PAGES:
            if v != vid:
                continue
            real = A.fit('<img src="%s" width="%d" height="%d" alt="%s, frame %s of video %d">' % (A.crop(frame, 0, 0, W, H, v), W, H, html.escape(title), frame, v), W, H)
            rebuilt = "".join('<div data-pt="%s" hidden>%s</div>' % (t, A.fit(page(t, fn, kind), W, H)) for t, _ in THEMES)
            cells.append(f'''<section class="scene" id="{pid}"><h3>{html.escape(title)}<span class="tag">video {v}, {frame} ({(int(frame[1:]) - 1) / 2:g} s)</span></h3><p class="why">{html.escape(why)}</p>
<div class="duo"><div class="cell"><p class="cap">The video</p>{real}</div><div class="cell"><p class="cap">Rebuilt</p>{rebuilt}</div></div></section>''')
    seg = "".join(f'<button type="button" data-theme-btn="{t}">{html.escape(n)}</button>' for t, n in THEMES)
    live = page("glow", v2_typing, "typing").replace('<div class="ag-ground"', '<div id="tl-ground" class="ag-ground"', 1)
    real0 = A.fit('<img src="%s" width="%d" height="%d" alt="the typing page in the video, frame f009">' % (A.crop("f009", 0, 0, W, H, 2), W, H), W, H)
    lab = f'''<h2 class="vid" style="margin-top:26px">Typing ground lab</h2>
<p class="lede">The first page's ground: a gradient, with three speckles on top: red across the page, a <b>light</b> one that clusters at the top-left, and a <b>dark</b> one that clusters at the bottom-right. Each corner should be almost full of its own colour. Each speckle has its own density through the middle and its own <b>maximum at each corner</b>. Change a slider and the preview below redraws (the corner masks are full-frame images, so it takes a moment).</p>
<div class="lab"><div class="lab-top"><div class="pair"><div class="cell"><p class="cap">The video, f009</p>{real0}</div>
<div class="cell"><p class="cap">Rebuilt <span id="tl-busy" hidden>(redrawing…)</span></p>{A.fit(live, W, H)}</div></div></div>
<div class="lab-ctl"><div id="tl-sliders"></div><div class="tabs"><button id="tl-reset" type="button">Reset to preset</button><button id="tl-copy" type="button">Copy parameters</button></div><pre id="tl-params" aria-live="polite"></pre></div></div>'''
    body = f'''<meta name="claude:viewport-fit-sides" content="cover">
<title>Agent Pages</title>
<style>{build.fontface()}{A.PAGE_CSS}{A.CSS}{A.LAB_CSS}{CSS}</style>
<div class="pg">
<h1>Agent pages</h1>
<p class="lede">Every full-screen composition the two reference videos show, rebuilt from the shared components and set beside the real frame. One switch re-themes the whole page; each page is the same size as the video's frame, scaled to fit.</p>
<div class="ctl"><div class="seg">{seg}</div>
 <label><input type="checkbox" id="set-stack"> Video above rebuild, at full width</label>
 <label><input type="checkbox" id="set-partner" checked> Partner logo white on dark grounds</label></div>
{lab}
{"".join(cells)}
</div>
<script>{A.BLOOM_JS}</script><script>{A.GROUND_JS}</script>
<script>AgGround.mountAll();</script>
{JS}
{LAB_JS}
'''
    os.makedirs(A.OUT, exist_ok=True)
    pth = os.path.join(A.OUT, "agent-pages.artifact.html")
    open(pth, "w", encoding="utf-8").write(body)
    open(os.path.join(A.OUT, "agent-pages.page.html"), "w", encoding="utf-8").write("<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'></head><body>" + body + "</body></html>")
    print(pth, len(body) // 1024, "KB")


if __name__ == "__main__":
    main()
