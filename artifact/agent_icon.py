#!/usr/bin/env python3
"""DEMO: the Cerebras mark broken into its parts (four orange arcs and the c) and animated: the arcs turn about the c, which stays still.

    python3 artifact/agent_icon.py
      -> out/agent-icon.artifact.html   the page body for the Artifact tool
      -> out/agent-icon.page.html       the same page as a local, standalone HTML file

A demo first: nothing in the components uses it yet. The old "working" mark spun the whole icon (c included); this one holds the c and turns only the arcs.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import build  # noqa: E402

SRC = open(os.path.join(ROOT, "brand/cerebras/cerebras_icon_white_orange.svg"), encoding="utf-8").read()
PATHS = re.findall(r'<path fill="(#[0-9A-Fa-f]+)" d="([^"]+)"', SRC, re.S)
ARCS = [re.sub(r"\s+", " ", d) for c, d in PATHS if c.upper() == "#F15A29"]
C = re.sub(r"\s+", " ", [d for c, d in PATHS if c.upper() == "#FFFFFF"][0])
assert len(ARCS) == 4
# the arcs are concentric about the c: centre in the icon's own box (the source translates by 32, 32; the arcs' circle is centred at -9.272, -8.457)
CX, CY = 32 - 9.272, 32 - 8.457

NAMES = ["Arc 1, outer", "Arc 2", "Arc 3", "Arc 4, inner"]


def icon(size, cls="", mode=None, parts="all", extra=""):
    """parts: all | one arc index | c"""
    g = ""
    if parts in ("all", "arcs") or isinstance(parts, int):
        for i, d in enumerate(ARCS):
            if isinstance(parts, int) and parts != i:
                continue
            g += f'<g class="arc a{i}"><path d="{d}" fill="#F15A29" transform="translate(32 32)"/></g>'
    if parts in ("all", "c"):
        g += f'<path class="c" d="{C}" transform="translate(32 32)"/>'
    return (f'<svg class="mk {cls}" width="{size}" height="{size}" viewBox="0 0 40.4 40.4" {extra} data-mode="{mode or ""}" '
            f'style="--cx:{CX:.3f}px;--cy:{CY:.3f}px"><g transform="translate(-2.6 -3.4)">{g}</g></svg>')


MODES = [
    ("together", "Together", "All four arcs turn the same way at one speed. The c holds still."),
    ("counter", "Counter-rotating", "Neighbouring arcs turn opposite ways, like a gyroscope."),
    ("cascade", "Cascade", "Each arc is a little slower than the one outside it, so the rings drift apart and meet again."),
    ("ripple", "Ripple", "Ramps up to full speed, then slows for a long settle: one turn per cycle, each arc starting a beat after the last, then a pause. Saved as the mark's spin option."),
]

CSS = """
:root { --bg:#f5f3f0; --card:#ffffff; --fg:#1d1a18; --muted:#6c6560; --line:#e4e0da; --accent:#c8441b; --stage:#ffffff; --cc:#1d1a18; --dk:#161212; --dk-fg:#f6efe9; --dk-muted:#a79c94; --mono:'Sometype Mono',ui-monospace,monospace; --sans:'Manrope',system-ui,sans-serif; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#141110; --card:#1d1917; --fg:#f2ece6; --muted:#a39a92; --line:#332d29; --accent:#ef7a50; --stage:#1d1917; --cc:#ffffff; color-scheme: dark; } }
:root[data-theme="dark"] { --bg:#141110; --card:#1d1917; --fg:#f2ece6; --muted:#a39a92; --line:#332d29; --accent:#ef7a50; --stage:#1d1917; --cc:#ffffff; color-scheme: dark; }
body { background: var(--bg); color: var(--fg); font-family: var(--sans); }
.ms { max-width: 1120px; margin: 0 auto; padding-block: 28px 64px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
.ms h1 { font-size: 30px; font-weight: 600; letter-spacing: -.02em; margin: 0 0 6px; }
.ms h2 { font-size: 19px; font-weight: 600; margin: 40px 0 6px; letter-spacing: -.01em; }
.ms p.lede { color: var(--muted); max-width: 66ch; margin: 0 0 14px; line-height: 1.55; font-size: 15px; }
.ms .cap { font-family: var(--mono); font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin: 0 0 8px; }
.ctl { display: flex; flex-wrap: wrap; gap: 14px 24px; align-items: center; padding: 14px 16px; background: var(--card); border: 1px solid var(--line); border-radius: 12px; }
.ctl label { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--muted); }
.ctl input[type=range] { width: 150px; accent-color: var(--accent); }
.ctl output { font-family: var(--mono); font-size: 12px; min-width: 3.4em; color: var(--fg); }
.ctl button { font: inherit; font-size: 13px; padding: 7px 14px; border-radius: 999px; border: 1px solid var(--line); background: var(--bg); color: var(--fg); cursor: pointer; }
.ctl button:focus-visible, .ctl input:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.modes { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 14px; margin-top: 14px; }
.mode { background: var(--card); border: 1px solid var(--line); border-radius: 14px; overflow: hidden; min-width: 0; }
.mode .st { display: grid; grid-template-columns: 1fr 1fr; }
.pane { display: grid; place-items: center; height: 150px; }
.pane.dk { background: var(--dk); } .pane.lt { background: #fbfaf8; }
.mode .tx { padding: 12px 14px 14px; } .mode h3 { margin: 0 0 4px; font-size: 15px; font-weight: 600; } .mode p { margin: 0; font-size: 13px; color: var(--muted); line-height: 1.5; }
.parts { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 12px; margin-top: 12px; }
.part { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 14px 10px 10px; text-align: center; min-width: 0; }
.part .pw { height: 110px; display: grid; place-items: center; }
.part span { display: block; font-size: 12px; color: var(--muted); margin-top: 8px; }
.inl { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(420px, 100%), 1fr)); gap: 14px; margin-top: 12px; }
.line { display: flex; align-items: center; gap: 10px; padding: 18px 20px; border-radius: 14px; font-size: 15px; font-weight: 500; }
.line.dk { background: var(--dk); color: var(--dk-fg); } .line.lt { background: #f9fbf8; color: #1f2328; border: 1px solid var(--line); }
.line .rule { flex: 1; height: 1px; background: currentColor; opacity: .18; }
.line small { font-weight: 400; opacity: .6; font-size: 12.5px; }
pre.out { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; font-family: var(--mono); font-size: 12px; overflow-x: auto; margin: 10px 0 0; }
/* the mark */
.mk { display: block; overflow: visible; }
.mk .c { fill: var(--cc); }
.pane.dk .mk .c, .line.dk .mk .c { fill: #fff; } .pane.lt .mk .c, .line.lt .mk .c { fill: #101010; }
.mk .arc { transform-origin: var(--cx) var(--cy); animation-play-state: var(--play, running); }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes spinr { to { transform: rotate(-360deg); } }
@keyframes ripple { 0% { transform: rotate(0); } 55%, 100% { transform: rotate(360deg); } }
.mk[data-mode="together"] .arc { animation: spin var(--t, 1.4s) linear infinite; }
.mk[data-mode="counter"] .arc { animation: spin var(--t, 1.4s) linear infinite; }
.mk[data-mode="counter"] .arc.a1, .mk[data-mode="counter"] .arc.a3 { animation-name: spinr; }
.mk[data-mode="cascade"] .arc.a0 { animation: spin calc(var(--t, 1.4s) * 1.0) linear infinite; }
.mk[data-mode="cascade"] .arc.a1 { animation: spin calc(var(--t, 1.4s) * 1.25) linear infinite; }
.mk[data-mode="cascade"] .arc.a2 { animation: spin calc(var(--t, 1.4s) * 1.55) linear infinite; }
.mk[data-mode="cascade"] .arc.a3 { animation: spin calc(var(--t, 1.4s) * 1.9) linear infinite; }
.mk[data-mode="ripple"] .arc { animation: ripple calc(var(--t, 1.4s) * 1.8) cubic-bezier(.5, 0, .1, 1) infinite; }   /* ramps up to full speed, then a long slow-down */
.mk[data-mode="ripple"] .arc.a1 { animation-delay: calc(var(--t, 1.4s) * .09); } .mk[data-mode="ripple"] .arc.a2 { animation-delay: calc(var(--t, 1.4s) * .18); } .mk[data-mode="ripple"] .arc.a3 { animation-delay: calc(var(--t, 1.4s) * .27); }
/* no reduced-motion rule here: this page exists to show the motion (the components that adopt it will honour the setting) */
"""

JS = """
<script>
(function(){
  var root=document.querySelector('.ms'),S={t:1.4,play:true},out=document.getElementById('o-out');
  function show(){out.textContent=JSON.stringify({secondsPerTurn:S.t,note:'modes: together, counter, cascade, ripple'},null,1)}
  function apply(){root.style.setProperty('--t',S.t+'s');root.style.setProperty('--play',S.play?'running':'paused');show()}
  var sp=document.getElementById('o-speed'),so=document.getElementById('o-speed-o'),pb=document.getElementById('o-play');
  sp.addEventListener('input',function(){S.t=+sp.value;so.textContent=S.t.toFixed(1)+' s';apply()});
  pb.addEventListener('click',function(){S.play=!S.play;pb.textContent=S.play?'Pause':'Play';apply()});
  document.getElementById('o-copy').addEventListener('click',function(){var b=this,t=out.textContent;function ok(m){b.textContent=m;setTimeout(function(){b.textContent='Copy settings'},1500)}
    try{navigator.clipboard.writeText(t).then(function(){ok('Copied')},function(){ok('Select the text below')})}catch(e){ok('Select the text below')}});
  apply();
})();
</script>
"""


def main():
    modes = ""
    for key, name, why in MODES:
        modes += (f'<div class="mode"><div class="st"><div class="pane dk">{icon(110, mode=key)}</div><div class="pane lt">{icon(110, mode=key)}</div></div>'
                  f'<div class="tx"><h3>{name}</h3><p>{why}</p></div></div>')
    parts = '<div class="part"><div class="pw">%s</div><span>Whole mark</span></div>' % icon(96, mode="")
    for i, n in enumerate(NAMES):
        parts += '<div class="part"><div class="pw">%s</div><span>%s</span></div>' % (icon(96, mode="", parts=i), n)
    parts += '<div class="part"><div class="pw">%s</div><span>Centre c (stays still)</span></div>' % icon(96, mode="", parts="c")
    lines = ""
    for tone in ("dk", "lt"):
        for key, name, _ in MODES[:1] + MODES[3:]:
            lines += (f'<div class="line {tone}">{icon(24, mode=key)}<span>Worked for 4 seconds</span><span class="rule"></span><small>{name}</small></div>')
    body = f'''<meta name="claude:viewport-fit-sides" content="cover">
<title>Cerebras Mark Spin</title>
<style>{build.fontface()}{CSS}</style>
<div class="ms">
<h1>Cerebras mark, spun in parts</h1>
<p class="lede">The icon beside "Worked for 4 seconds" and the live meter used to turn as one piece. Here it is split into four orange arcs and the c, and only the arcs turn, about the c. This is a demo: no component uses it yet. Pick the motion you like and I will apply it everywhere the mark spins.</p>
<div class="ctl"><label>Seconds per turn <input id="o-speed" type="range" min="0.4" max="4" step="0.1" value="1.4"><output id="o-speed-o">1.4 s</output></label>
<button id="o-play" type="button">Pause</button><button id="o-copy" type="button">Copy settings</button></div>
<pre class="out" id="o-out"></pre>
<h2>Four motions</h2>
<p class="lede">Each card shows the mark on the dark window and on the light one. The c is the same shape in both, white on dark and near-black on light.</p>
<div class="modes">{modes}</div>
<h2>At the size it is used</h2>
<p class="lede">The mark is 20 to 26 px beside the line and the meter, so a motion has to read at that size. Together and Ripple are shown here.</p>
<div class="inl">{lines}</div>
<h2>The parts</h2>
<p class="lede">The source file has five paths: four orange arcs and one c. The arcs are concentric about the c's centre, which is the point they turn around.</p>
<div class="parts">{parts}</div>
</div>
{JS}
'''
    out = os.path.join(ROOT, "out")
    os.makedirs(out, exist_ok=True)
    pth = os.path.join(out, "agent-icon.artifact.html")
    open(pth, "w", encoding="utf-8").write(body)
    open(os.path.join(out, "agent-icon.page.html"), "w", encoding="utf-8").write(
        "<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'></head><body>" + body + "</body></html>")
    print(pth, len(body) // 1024, "KB")


if __name__ == "__main__":
    main()
