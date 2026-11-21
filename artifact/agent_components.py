#!/usr/bin/env python3
"""The agent components, next to the video they came from.

    python3 artifact/agent_components.py
      -> out/agent-components.artifact.html   the page body for the Artifact tool
      -> out/agent-components.page.html       the same page as a local, standalone HTML file

For every component the reference video draws, one row: the REAL frame crop, the
rebuild on the video's own theme (ember), and the same rebuild on the ORIGINAL
comparison theme (paper). The rebuild is components/agent/agent.css: tokens only,
no kit, no layout. The geometry table at the top is measured live in the viewer's
browser (offsetWidth / offsetHeight of the rebuilt parts) against numbers read off
the video's frames, so a drift shows as a percentage, not as an opinion.

The frames are out/_reference/agent-browser-walmart/ (gitignored; extract them
again from the video the way a reference video says).
"""
import base64, html, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import build  # noqa: E402

FRAMES = {1: os.path.join(ROOT, "out", "_reference", "agent-browser-walmart"), 2: os.path.join(ROOT, "out", "_reference", "video2"), 3: os.path.join(ROOT, "out", "_reference", "video3"), 4: os.path.join(ROOT, "out", "_reference", "video4")}
CSS = open(os.path.join(ROOT, "components", "agent", "agent.css"), encoding="utf-8").read()
GROUND_JS = open(os.path.join(ROOT, "components", "agent", "ground.js"), encoding="utf-8").read()
BLOOM_JS = open(os.path.join(ROOT, "components", "agent", "bloom.js"), encoding="utf-8").read()
OUT = os.path.join(ROOT, "out")
# NUDGE: per-builder (dx, dy) in px, written by tools/align.py when the diff against the video measures a definitive offset. stage() moves a builder's content by it.
NUDGE = json.load(open(os.path.join(HERE, "agent_nudge.json"))) if os.path.exists(os.path.join(HERE, "agent_nudge.json")) else {}


# ── the real frames, cropped ────────────────────────────────────────────────
def crop(frame, x, y, w, h, v=1):
    p = os.path.join(FRAMES[v], f"{frame}.jpg")
    if not os.path.exists(p):
        sys.exit(f"missing {p}: extract the reference frames first")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", f"crop={w}:{h}:{x}:{y}", "-q:v", "3", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
                         check=True, capture_output=True).stdout
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode()


# ── icons and marks (strokes, drawn once; the house mark is a brand file) ───
P = {
 "plus": '<path d="M12 5v14M5 12h14"/>', "mic": '<rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 11a7 7 0 0014 0M12 18v3"/>',
 "chev": '<path d="M6 9l6 6 6-6"/>', "up": '<path d="M12 19V5M6 11l6-6 6 6"/>', "stop": '<rect x="7" y="7" width="10" height="10" rx="2" fill="currentColor" stroke="none"/>',
 "expand": '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>', "swap": '<path d="M7 4L3 8l4 4M3 8h14M17 20l4-4-4-4M21 16H7"/>',
 "cols": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M12 4v16"/>', "panel": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/>',
 "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>',
 "more": '<circle cx="5" cy="12" r="1.2" fill="currentColor"/><circle cx="12" cy="12" r="1.2" fill="currentColor"/><circle cx="19" cy="12" r="1.2" fill="currentColor"/>',
 "back": '<path d="M15 6l-6 6 6 6"/>', "fwd": '<path d="M9 6l6 6-6 6"/>', "reload": '<path d="M20 12a8 8 0 11-2.3-5.7M20 4v5h-5"/>',
 "ext": '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5"/>', "dl": '<path d="M12 4v11M7 11l5 5 5-5M5 20h14"/>',
 "edit": '<path d="M4 20l4-1 11-11a2.1 2.1 0 00-3-3L5 16l-1 4z"/>', "ptr": '<path d="M4 4l7 17 2.5-7.5L21 11 4 4z"/>', "close": '<path d="M6 6l12 12M18 6L6 18"/>',
 "copy": '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 012-2h9"/>', "monitor": '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
 "browser": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18"/>',
 "puzzle": '<path d="M19.4 7.85c-.05.32.06.65.29.88l1.57 1.57c.47.47.71 1.09.71 1.7s-.24 1.23-.71 1.7l-1.61 1.61a.98.98 0 0 1-.84.28c-.47-.07-.8-.48-.97-.93a2.5 2.5 0 1 0-3.21 3.21c.45.17.86.5.93.97a.98.98 0 0 1-.28.84l-1.61 1.61a2.4 2.4 0 0 1-1.7.71 2.4 2.4 0 0 1-1.7-.71l-1.57-1.57a1.03 1.03 0 0 0-.88-.29c-.49.07-.84.5-1.02.97a2.5 2.5 0 1 1-3.24-3.24c.47-.18.9-.53.97-1.02a1.03 1.03 0 0 0-.29-.88l-1.57-1.57A2.4 2.4 0 0 1 2 12c0-.62.24-1.23.71-1.7l1.52-1.53c.24-.24.58-.35.92-.3.52.08.88.53 1.07 1.01a2.5 2.5 0 1 0 3.26-3.26c-.48-.2-.93-.56-1.01-1.07-.05-.34.06-.68.3-.92l1.52-1.53A2.4 2.4 0 0 1 12 2c.62 0 1.23.24 1.7.71l1.57 1.57c.23.23.56.34.88.29.49-.07.84-.5 1.02-.97a2.5 2.5 0 1 1 3.24 3.24c-.47.18-.9.53-.97 1.02Z"/>',
 "file": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
 "braces": '<path d="M8 3H7a2 2 0 0 0-2 2v5a2 2 0 0 1-2 2 2 2 0 0 1 2 2v5a2 2 0 0 0 2 2h1M16 3h1a2 2 0 0 1 2 2v5a2 2 0 0 0 2 2 2 2 0 0 0-2 2v5a2 2 0 0 1-2 2h-1"/>',
 "ring": '<path d="M12 3a9 9 0 1 0 9 9" opacity=".9"/><circle cx="12" cy="12" r="9" opacity=".25"/>', "spinner": '<path d="M12 3a9 9 0 019 9" />',
}


def ic(name, s=20, sw=1.8, cls=""):
    return (f'<svg class="ag-ic {cls}" width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round">{P[name]}</svg>')


_icon = lambda f: build.inline_file(ROOT, "brand/cerebras/" + f)
MARK_D, MARK_L = _icon("cerebras_icon_white_orange.svg"), _icon("cerebras_icon_black_orange.svg")
LOGO = _icon("cerebras_logo.svg")
_KIMI = os.path.join(ROOT, "kits", "kimi", "brand", "moonshot_logo.svg")   # the first partner kit's mark; a checkout without that kit falls back to the template's neutral stand-in
PARTNER = build.inline_file(ROOT, _KIMI if os.path.exists(_KIMI) else "templates/agent-film/partner-logo.svg")


def mark(s):
    return (f'<span class="ag-mark" style="width:{s}px;height:{s}px"><span class="ag-mark-d">{MARK_D}</span>'
            f'<span class="ag-mark-l">{MARK_L}</span></span>')


def mark_spin(s):
    """The mark with the ripple spin: the arcs turn about the c (an option; no component uses it yet). See artifact/agent_icon.py for the demo."""
    import agent_icon
    return agent_icon.icon(s, mode="ripple")


def logo(h, svg=LOGO, cls=""):
    return f'<span class="ag-logo {cls}" style="height:{h}px">{svg}</span>'


# ── the reference's words ───────────────────────────────────────────────────
PROMPT_1 = "Go to Walmart and compare the Ninja AF140 and AF180 air fryers. Compare their price, capacity,"
PROMPT_2 = "cooking modes, and cleaning features. Recommend which is better for a household of four and"
PROMPT_3 = "explain why. Check out with the best one."


NEST = False   # True while a component is built INSIDE a full page: transparent, and no ground of its own (the page draws one ground behind everything)
FRAME_OFF = (0, 0)   # where the component being built sits in the 1920 x 1080 video frame: row() sets it from the crop box before it calls a builder


def gnd(kind, glow=None):
    """A ground the size of the WHOLE frame, shifted by the crop's offset, so every component shows its own slice of one ground (the gradient's angle, reaches and
    grid mean the same thing everywhere, and its blur and specks are in the video's own pixels) instead of squeezing a whole gradient into a small box."""
    if NEST:
        return ""
    x, y = FRAME_OFF
    g = ' data-glow="%s"' % glow if glow else ""
    return '<div class="ag-ground" data-ground="%s"%s style="inset:auto;left:%dpx;top:%dpx;width:1920px;height:1080px"></div>' % (kind, g, -x, -y)


def stage(theme, w, h, inner, bg=None, dim=False, kind=None):
    nd = NUDGE.get(sys._getframe(1).f_code.co_name)   # the calling builder's name: c_tool, c2_answer, c3_pane ...
    if nd and (nd[0] or nd[1]):
        inner = '<div style="position:absolute;left:0;top:0;width:100%%;height:100%%;transform:translate(%gpx,%gpx)">%s</div>' % (nd[0], nd[1], inner)
    st = f"width:{w}px;height:{h}px;" + ("background:transparent;overflow:visible;" if NEST else f"background:{bg};" if bg else "")
    ground = "" if (bg or NEST) else gnd("dim" if dim else "bright")
    cls = "ag ag-dim" if dim else "ag"
    k = f' data-kind="{kind}"' if kind else ""
    return f'<div class="{cls}" data-theme="{theme}" data-partner="white"{k} style="{st}">{ground}{inner}</div>'


def model_pill(size, dimmed=False, chev="var(--ink-2)", name="Kimi K3.1 Pro"):
    return (f'<span class="ag-model{" ag-dimmed" if dimmed else ""}" style="font-size:{size}px;gap:{size * .35:.0f}px;--chev:{chev}">{name}'
            f'{ic("chev", size * .7, 2.2)}</span>')


# ── the components, as (theme) -> html at the video's own pixel scale ───────
def c_ground(t):
    return stage(t, 640, 360, "")


def c_composer_hero(t):
    send = f'<span class="ag-send" style="width:66px;height:66px;color:var(--card)">{ic("up", 30, 2.2)}</span>'
    return stage(t, 1620, 400, f'''
<div class="ag-composer" data-m="composer-hero" style="left:24px;top:26px;width:1572px;height:348px;border-radius:44px">
  <div class="ag-text" style="padding:34px 32px;font-size:32px;line-height:49px">{PROMPT_1}<br>cooking modes, and cleaning features. Recommend which i<span class="ag-caret"></span></div>
  <div class="ag-bar" style="left:30px;right:20px;bottom:21px;height:66px;gap:32px">
    <span style="color:var(--ink)">{ic("plus", 36, 1.8)}</span><span style="flex:1"></span>
    <span style="display:flex;align-items:center;gap:20px">{model_pill(26)}</span><span style="color:var(--ink-2)">{ic("mic", 28, 1.8)}</span>{send}
  </div>
</div>''')


def c_composer_docked(t):
    return stage(t, 810, 160, f'''
<div class="ag-composer" data-m="composer-docked" style="left:16px;top:17px;width:765px;height:125px;border-radius:24px;box-shadow:none;background:var(--card-2)">
  <div class="ag-text" style="padding:19px 16px;font-size:20px;line-height:26px"><span class="ag-ph">Message Cerebras</span></div>
  <div class="ag-bar" style="left:16px;right:14px;bottom:12px;height:40px;gap:22px">
    <span style="color:var(--ink-3)">{ic("plus", 24, 1.8)}</span><span style="flex:1"></span>{model_pill(16, True, "var(--ink-3)")}<span style="color:var(--ink)">{ic("mic", 20, 1.8)}</span>
    <span class="ag-send stop" style="width:38px;height:38px">{ic("stop", 25)}</span>
  </div>
</div>''', bg="var(--window)")


def titlebar(tools_on=True, model="Kimi K3.1 Pro", short=False):
    names = ("panel", "globe", "cols", "more") if short else ("expand", "swap", "cols", "panel", "globe", "cols", "more")
    tools = "".join(ic(n, 21 if not short else 17, 1.7) for n in names) if tools_on else ""
    mdl = f'<span class="ag-appmodel" style="margin-left:14px">{model}</span>' if model else ""
    return f'''<div class="ag-titlebar" data-m="titlebar"><div class="ag-lights"><i></i><i></i><i></i></div>
  <span style="margin-left:22px">{mark(32)}</span><span class="ag-appname" style="margin-left:12px">Cerebras</span>{mdl}
  <span style="flex:1"></span><span class="ag-tools" style="margin-right:36px">{tools}</span></div>'''


def c_titlebar(t):
    return stage(t, 810, 84, titlebar(), bg="var(--window)")


def c_welcome(t):
    send = f'<span class="ag-send idle" style="width:38px;height:38px">{ic("up", 20, 2.2)}</span>'
    return stage(t, 1608, 992, f'''
<div class="ag-window" data-m="window" style="left:0;top:0;width:1608px;height:992px;border-radius:20px;border:0;box-shadow:none">
  {titlebar(False)}
  <span style="position:absolute;left:776px;top:166px">{mark(44)}</span>
  <div class="ag-welcome-h" style="top:246px">What would you like to do?</div>
  <div class="ag-composer" data-m="composer-welcome" style="left:372px;top:371px;width:860px;height:156px;border-radius:22px;box-shadow:none;background:var(--card-2)">
    <div class="ag-text" style="padding:16px 16px;font-size:18px;line-height:27px">{PROMPT_1}<br>{PROMPT_2}<br>{PROMPT_3}<span class="ag-caret"></span></div>
    <div class="ag-bar" style="left:16px;right:12px;bottom:10px;height:38px;gap:22px"><span style="color:var(--ink-2)">{ic("plus", 22, 1.8)}</span><span style="flex:1"></span>{model_pill(15)}<span style="color:var(--ink-2)">{ic("mic", 19, 1.8)}</span>{send}</div>
  </div>
</div>''', bg="var(--ground)")


def c_chat(t):
    return stage(t, 810, 330, f'''
<div class="ag-bubble" data-m="bubble" style="left:263px;top:31px;width:488px">Go to Walmart and compare the Ninja AF140 and AF180 air fryers. Compare their price, capacity, cooking modes, and cleaning features. Recommend which is better for a household of four and explain why. Check out with the best one.</div>
<div class="ag-status" style="left:49px;top:206px">{mark(26)}<span style="margin-left:6px">Waiting for a response...</span><span style="margin-left:2px">1s</span></div>''', bg="var(--window)")


def shot_html():
    """a neutral storefront thumbnail: a bar, a search pill, tiles (not any real brand's page)"""
    tiles = "".join(f'<i style="position:absolute;left:{14 + i * 86}px;top:150px;width:76px;height:96px;border-radius:8px;background:#e9ecf1"></i>' for i in range(4))
    return ('<div style="position:absolute;inset:0"><div style="height:32px;background:#2a5db0"></div>'
            '<i style="position:absolute;left:44px;top:8px;width:230px;height:16px;border-radius:8px;background:#fff;opacity:.9"></i>'
            '<i style="position:absolute;left:14px;top:48px;width:110px;height:84px;border-radius:8px;background:#dfe6f3"></i>'
            '<i style="position:absolute;left:132px;top:48px;width:110px;height:84px;border-radius:8px;background:#f1e6d4"></i>'
            '<i style="position:absolute;left:250px;top:48px;width:94px;height:84px;border-radius:8px;background:#e6efe2"></i>' + tiles + '</div>')


def c_tool(t):
    return stage(t, 450, 430, f'''
<span style="position:absolute;left:25px;top:8px">{mark(30)}</span>
<div class="ag-toolhead" style="left:66px;top:9px">{ic("browser", 19, 1.8)}<span style="margin-left:4px">Using Browser</span>{ic("fwd", 14, 2)}</div>
<div class="ag-tool" data-m="tool" style="left:61px;top:45px;width:358px;height:315px">
  <div class="ag-shot" style="height:267px">{shot_html()}</div>
  <div class="ag-cap"><span style="color:var(--ink-2)">{ic("globe", 20, 1.6)}</span><span>Walmart</span></div>
</div>
<div class="ag-meter" style="left:61px;top:382px"><span class="ag-spin" style="display:block">{mark(24)}</span><span>3s · 309 output tokens ·</span><span class="ag-chip">943 tok/s</span></div>''', bg="var(--window)")


def c_browser(t):
    tabs = "".join(f'<span class="ag-tab{" on" if on else ""}">{ic("monitor", 18, 1.6)}<span>{name}</span>{ic("close", 14, 2) if on else ""}</span>'
                   for name, on in (("Walmart | Sa", False), ("Cart -", False), ("Ninja Air Fryer Pro XL 5", False), ("Ninja Air Fryer Pro XL 5", True)))
    nav = "".join(f'<span>{ic(n, 20, 1.8)}</span>' for n in ("plus", "back", "fwd", "reload"))
    right = "".join(f'<span>{ic(n, 20, 1.7)}</span>' for n in ("ext", "dl", "edit", "ptr"))
    return stage(t, 799, 200, f'''
<div class="ag-browser" style="left:0;top:0;width:799px;height:200px">
  <div class="ag-tabs">{tabs}<span style="flex:1"></span><span>{ic("plus", 20)}</span><span style="margin-left:14px">{ic("expand", 20)}</span><span style="margin-left:14px">{ic("close", 20)}</span></div>
  <div class="ag-nav">{nav}<span class="ag-url" data-m="url">walmart.com/#product/ninja-af140</span>{right}</div>
  <div class="ag-pagearea" style="top:127px"></div>
</div>''', bg="var(--window)")


def c_answer(t):
    chip = '<span class="ag-chip">1950 tok/s · TTFT 640 ms</span>'
    return stage(t, 650, 760, f'''
<div style="position:absolute;left:10px;top:10px;width:615px">
<div class="ag-answer" data-m="answer" style="position:relative;width:615px">
  <h4>Recommendation: Ninja AF180</h4>
  <p>For a household of four, the larger basket and dishwasher-safe cleanup make the <b>AF180</b> the better choice. It costs <b>$18.03 more</b> than the AF140, but provides <b>1.5 quarts more capacity</b> and an extra cooking mode, making family-sized meals easier with less batch cooking.</p>
  <table class="ag-table"><thead><tr><th style="width:116px">Feature</th><th style="width:195px">Ninja AF140</th><th>Ninja AF180</th></tr></thead><tbody>
   <tr><td>Price</td><td><b>$79.97</b></td><td><b>$98.00</b></td></tr>
   <tr><td>Capacity</td><td>5 qt</td><td><b>6.5 qt</b></td></tr>
   <tr><td>Cooking modes</td><td>Air Fry, Reheat, Dehydrate</td><td>Air Fry, <b>Air Roast</b>, Reheat, Dehydrate</td></tr>
   <tr><td>Cleaning</td><td>Nonstick basket and crisper plate</td><td>Nonstick <b>dishwasher-safe</b> basket and crisper plate</td></tr></tbody></table>
  <div class="ag-table-tools"><span>{ic("expand", 18, 1.8)}Expand table</span><span>{ic("copy", 20, 1.8)}</span></div>
  <p style="margin-top:22px"><b>Checked out:</b> The AF180 was purchased for <b>$98.00</b>, with free shipping and an estimated delivery date of <b>Sunday, November 8</b>. The order total is <b>$106.63</b>, including tax.</p>
  <span class="ag-redact"></span>
</div>
<div class="ag-foot" style="position:static;margin:22px 0 0 1px">Done in 12 seconds · 2.3k output tokens</div>
<div class="ag-foot" style="position:static;margin:6px 0 0 1px;display:flex;align-items:center">Assistant{chip}<span>just now</span></div>
</div>''', bg="var(--window)")


def c_claim(t):
    return stage(t, 1920, 740, f'''
{gnd("dim")}
<div class="ag-claim-h" data-m="claim-h" style="top:78px;font-weight:500">Kimi K3.1 Pro</div>
<div class="ag-claim-l" style="top:242px">Up to <span class="ag-n">2,000</span> tokens per second<sup>*</sup></div>
<div class="ag-claim-f" style="top:672px">*Based on internal prerelease results. Observed speed may vary by workload and configuration.</div>''', bg="var(--ground-dim)", dim=True, kind="claim")


def c_lockup(t):
    return stage(t, 1120, 280, f'''
{gnd("dim")}
<div class="ag-lockup" style="top:49px;height:182px">{logo(182)}<span class="ag-hair"></span>{logo(104, PARTNER, "ag-logo-partner")}</div>''', bg="var(--ground-dim)", dim=True, kind="lockup")


def c_redaction(t):
    return stage(t, 520, 140, '''
<div style="position:absolute;inset:0;background:var(--page);color:var(--on-page);padding:22px 0 0 16px">
  <div style="display:flex;align-items:center;gap:14px;font-size:32px;font-weight:700;letter-spacing:-.01em">
    <span style="width:40px;height:40px;border-radius:50%;background:#2a8a3a;display:grid;place-items:center;color:#fff"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5 9-10"/></svg></span>
    <span>Thanks for your order, <span class="ag-blur">Alex M.</span></span></div>
  <div style="margin:14px 0 0 54px;font-size:18px">We're sending a confirmation email to <span class="ag-blur">alex.m@example.com</span></div>
  <div style="margin:14px 0 0 0;font-size:16px">Order # <span class="ag-blur">0000000-00000</span></div></div>''', bg="var(--page)")



# ── the second reference's components (a reference video) ─────
def c2_ground(t):
    return stage(t, 800, 300, "")


def c2_composer(t):
    send = '<span class="ag-send" style="width:47px;height:47px;color:var(--card)">' + ic("up", 22, 2.2) + '</span>'
    return stage(t, 1260, 260, f'''
<div class="ag-composer" data-m="composer-2" style="left:40px;top:39px;width:1180px;height:182px;border-radius:28px">
  <div class="ag-text" style="padding:24px 26px;font-size:25px;line-height:32px">Review the pricing page for the upcoming launch. Are there any improvements we can make <span class="ag-caret" style="height:1.1em"></span></div>
  <div class="ag-bar" style="left:26px;right:19px;bottom:20px;height:48px;gap:26px">
    <span style="color:var(--ink)">{ic("plus", 26, 1.7)}</span><span style="flex:1"></span>
    {model_pill(20, False, "var(--ink-2)", "Muse Spark Open")}<span style="color:var(--ink-2)">{ic("mic", 24, 1.7)}</span>{send}
  </div>
</div>''')


def c2_welcome(t):
    send = '<span class="ag-send" style="width:26px;height:26px;color:var(--card)">' + ic("up", 13, 2.4) + '</span>'
    return stage(t, 1528, 900, f'''
<div class="ag-window" data-m="window-2" style="left:0;top:0;width:1528px;height:900px;border-radius:28px;border:0;box-shadow:none">
  {titlebar(False, None)}<span style="position:absolute;right:26px;top:26px;color:var(--ink-3)">{ic("panel", 16, 1.7)}</span>
  <span style="position:absolute;left:737px;top:337px">{mark(54)}</span>
  <div class="ag-welcome-h" style="top:431px;font-size:38px;font-weight:700;color:var(--ink)">What would you like to do?</div>
  <div class="ag-composer" data-m="composer-welcome-2" style="left:374px;top:532px;width:780px;height:114px;border-radius:16px;box-shadow:none;border:1px solid var(--line)">
    <div class="ag-text" style="padding:13px 15px;font-size:13.5px;line-height:19px">Review the pricing page for the upcoming launch. Are there any improvements we can make to the<br>copy?<span class="ag-caret"></span></div>
    <div class="ag-bar" style="left:14px;right:14px;bottom:9px;height:28px;gap:16px"><span style="color:var(--ink-2)">{ic("plus", 16, 1.8)}</span><span style="flex:1"></span>{model_pill(11, False, "var(--ink-2)", "Muse Spark Open")}<span style="color:var(--ink-2)">{ic("mic", 14, 1.8)}</span>{send}</div>
  </div>
</div>''')


def c2_turn(t):
    chip = '<span class="ag-chip">2,270 toks/s · TTFT 31 ms</span>'
    return stage(t, 860, 280, f'''
<div class="ag-bubble" data-m="bubble-2" style="left:258px;top:15px;width:514px;padding:16px 17px;font-size:15.5px;border-radius:18px">Review the pricing page for the upcoming launch. Are there any improvements we can make to the copy?</div>
<span style="position:absolute;left:18px;top:140px">{mark(26)}</span>
<div class="ag-pill" style="left:63px;top:136px;font-size:14.5px">Pricing copy check — I'll pull your pricing page and review it for opportunities.</div>
<div class="ag-toolrow" style="left:66px;top:192px">{ic("puzzle", 17, 1.5)}<span>Composio Composio Search Tools</span>{ic("fwd", 12, 2)}</div>
<div class="ag-meter" style="left:64px;top:233px"><span class="ag-spin" style="display:block">{mark(20)}</span><span>2s · 230 output tokens ·</span>{chip}</div>''', bg="var(--window)")


def c2_answer(t):
    chip = '<span class="ag-chip" style="height:22px;font-size:12.5px;padding:0 9px;margin:0 8px">2,722 toks/s · TTFT 31 ms</span>'
    code = lambda x: '<span class="ag-code">%s</span>' % x
    link = lambda ico, x: '<span class="ag-flink">%s%s</span>' % (ic(ico, 13, 1.7), x)
    return stage(t, 780, 600, f'''
<span style="position:absolute;left:18px;top:14px">{mark(26)}</span>
<div style="position:absolute;left:63px;top:14px;width:662px">
  <div class="ag-worked" style="position:static">Worked for 4 seconds {ic("fwd", 12, 2)}</div>
  <div class="ag-reply" data-m="reply-2" style="position:relative;margin-top:8px;width:662px">
    <p>Here's your review of {link("braces", "pricing.json")} against {link("file", "pricing-review-brief.md")} and the Linear issues:</p>
    <p><b>Current copy has 3 inaccuracies against approved policy (no action taken yet):</b></p>
    <ol>
      <li><b>Hero claim</b> — says "Unlimited projects on every plan" but approved limits are Starter: 3, Growth: 20, Enterprise: unlimited. This is tracked as MKT-102. Suggested fix in brief: "Simple pricing that grows with your team. Choose the plan that fits your projects."</li>
      <li><b>Missing annual disclosure</b> — cards show monthly $49 / $149 and equivalents $39.20 / $119.20 (20% off) but {code("annualDisclosure")} is empty. Per MKT-103, should also disclose <b>Starter $470.40/year</b> and <b>Growth $1,430.40/year</b> billed annually, keep monthly option, and note taxes excluded + allowances reset monthly.</li>
      <li><b>Contradictory trial footer</b> — trial is correctly configured as 14 days with {code("creditCardRequired: false")} and CTA "Start free trial" (MKT-104, confirmed in MKT-108), but {code("trial.footer")} still says "Credit card required". Should be "No credit card required".</li>
    </ol>
    <p>All pricing values themselves (tier prices, seats, event allowances) are unchanged per the brief.</p>
    <p>Status is {code("on track")} — these are owned by Vikram Fontaine (reviewer Lucia Ibarra), scheduled review June 11, 3 PM EDT. No approval is pending from you — optional feedback/PRs are welcome.</p>
    <p>Want me to open a PR with these fixes, or just leave as optional feedback for Vikram/Lucia?</p>
  </div>
  <div class="ag-foot" style="position:static;margin:12px 0 0 0;font-size:12.5px">Done in 4 seconds · 1.3k output tokens</div>
  <div class="ag-foot" style="position:static;margin:6px 0 0 0;font-size:12.5px;display:flex;align-items:center">Cerebras{chip}<span>just now</span></div>
</div>''', bg="var(--window)")


def c2_docked(t, state="done"):
    """state "done": the rate chip in the bar, a spinner and a disabled send (the finished turn); "stop": the bar while the model is writing, with the stop button"""
    chip = '<span class="ag-chip" style="height:20px;font-size:11.5px;padding:0 8px">2,722 toks/s · TTFT 31 ms</span>'
    if state == "stop":
        mid = f'''{model_pill(14, True, "var(--ink-3)", "Muse Spark Open")}<span style="color:var(--ink)">{ic("mic", 17, 1.7)}</span><span class="ag-send stop" style="width:32px;height:32px">{ic("stop", 18)}</span>'''
        lead = ""
    else:
        mid = f'''{model_pill(14, False, "var(--ink-2)", "Muse Spark Open")}<span class="ag-spin" style="color:var(--ink-3)">{ic("ring", 16, 2)}</span><span style="color:var(--ink-2)">{ic("mic", 17, 1.7)}</span><span class="ag-send off" style="width:32px;height:32px">{ic("up", 16, 2.2)}</span>'''
        lead = chip
    return stage(t, 800, 140, f'''
<div class="ag-composer" data-m="composer-docked-2" style="left:11px;top:15px;width:777px;height:113px;border-radius:20px;box-shadow:none;border:1px solid var(--line);background:var(--card-2)">
  <div class="ag-text" style="padding:15px 16px;font-size:17px;line-height:22px"><span class="ag-ph">Message Cerebras</span></div>
  <div class="ag-bar" style="left:16px;right:14px;bottom:8px;height:34px;gap:18px">
    <span style="color:var(--ink-2)">{ic("plus", 20, 1.7)}</span>{lead}<span style="flex:1"></span>{mid}
  </div>
</div>''', bg="var(--window)")


def c2_caption(t):
    return stage(t, 520, 80, '<div class="ag-caption" style="top:24px">Demo shown with mock data.</div>')


def c2_card(t):
    tabs = "".join('<span class="%s">%s</span>' % ("on" if n == "Pull requests" else "", n) for n in ("Code", "Issues", "Pull requests", "Actions", "Projects", "Insights"))
    return stage(t, 1450, 860, f'''
<div style="position:absolute;left:5px;top:12px;width:1433px;height:843px;border-radius:16px;overflow:hidden;filter:blur(4px)"><div class="ag-blurred" style="position:absolute;left:-90px;top:-90px;width:1613px;height:1023px;background:var(--window)"><div style="position:absolute;left:90px;top:90px;width:1433px;height:843px">
  {titlebar(True, "Muse Spark Open", short=True)}<div class="ag-bubble" style="left:590px;top:96px;width:514px;padding:16px 17px;font-size:15.5px">Don't overpromise unlimited usage, make the billing cycles clear, and no credit card will be required. Fix all three in one draft PR.</div></div></div></div>
<div class="ag-pr" data-m="pr-card" style="left:57px;top:147px;width:1326px;height:585px">
  <div class="ag-pr-head"><div class="ag-pr-repo">{ic("browser", 22, 1.6)}<span>newco-analytics / <b>analytics-pro-web</b></span></div><div class="ag-pr-tabs">{tabs}</div></div>
  <div class="ag-pr-body">
    <div class="ag-pr-title">Fix pricing copy: hero limits, annual billing, trial footer (MKT-102, MKT-103, MKT-104) <i>#19</i></div>
    <div class="ag-pr-meta"><span class="ag-badge">{ic("swap", 18, 2)}Draft</span><b>newco-team</b> wants to merge 1 commit into <span class="ag-branch">main</span> from <span class="ag-branch">fix/pricing-copy-MKT-102-104</span></div>
    <div class="ag-pr-sub"><span><b>Conversation</b><i class="ag-n">0</i></span><span>Commits<i class="ag-n">1</i></span><span>Checks<i class="ag-n">2</i></span><span>Files changed<i class="ag-n">1</i></span><span style="flex:1"></span><span style="color:#2e8b3d">+6</span><span style="color:#cf222e">−3</span><span class="ag-diffsq" style="margin-left:0"><i></i><i></i><i></i><i class="r"></i><i class="r"></i></span></div>
    <div class="ag-pr-text">Owner: Vikram Fontaine · Reviewer: Lucia Ibarra<div style="height:8px"></div>Fixes:<br>• MKT-102: Replace "Unlimited projects on every plan" hero with "Choose the plan that fits your projects."<br>• MKT-103: Disclose annual totals: Starter $470.40/year, Growth $1,430.40/year<br>• MKT-104: Align trial footer to "No credit card required" (14-day trial)<div style="height:7px"></div>No changes to tier prices, seats, or monthly event allowances.</div>
  </div>
</div>''')


def c2_claim(t):
    return stage(t, 1920, 680, f'''
{gnd("dim")}
<div class="ag-claim-h" data-m="claim-h-2" style="top:50px;font-size:82px;letter-spacing:-.03em;font-weight:500">Muse Spark Open</div>
<div class="ag-claim-l ag-spaced" style="top:174px;font-size:45px;letter-spacing:-.02em;font-weight:400">Up to <span class="ag-n">3,000</span> tokens per second<sup>*</sup></div>
<div class="ag-claim-f" style="top:609px;font-size:17px">*Observed during this session on Cerebras. Speed may vary by workload and configuration. Mock data shown.</div>''', bg="var(--ground-dim)", dim=True, kind="claim")


def c2_lockup(t):
    return stage(t, 1100, 260, f'''
{gnd("dim")}
<div class="ag-lockup" style="top:44px;height:172px;gap:34px"><span class="ag-poweredby" style="font-size:96px;line-height:172px">powered by</span>{logo(172)}</div>''', bg="var(--ground-dim)", dim=True, kind="lockup")


# ── the third reference's components (a reference video): same app, a vermilion halftone ground, a timer pill, a browser pane, an order card ──
def c3_ground(t):
    return stage(t, 800, 300, "")


def c3_composer(t):
    """the hero composer: a wide white pill, the plus, the mic and a pale-blue send, all on the card's centre line; the typed prompt wraps in the middle"""
    return stage(t, 1800, 440, f'''
<div class="ag-composer" data-m="composer-3" style="left:60px;top:60px;width:1680px;height:320px;border-radius:64px">
  <div class="ag-text" style="left:132px;right:auto;width:1340px;padding:36px 0 0;font-size:43px;font-weight:500;line-height:60px;letter-spacing:-.01em">Check Best Buy for the new LG UltraGear 45-inch 5K OLED monitor. If it's available, buy one and confirm the order details.</div>
  <span style="position:absolute;left:40px;top:135px;color:var(--ink)">{ic("plus", 50, 2.2)}</span>
  <span style="position:absolute;left:1446px;top:134px;color:var(--ink)">{ic("mic", 50, 1.9)}</span>
  <span class="ag-send idle" style="position:absolute;left:1550px;top:110px;width:100px;height:100px">{ic("up", 46, 1.8)}</span>
</div>''')


def c3_timer(t, text="0.6s"):
    return stage(t, 190, 56, '<span class="ag-timer" data-m="timer" style="left:12px;top:4px;width:160px;height:46px;font-size:26px">%s</span>' % text, bg="var(--window)")


def c3_welcome(t):
    send = '<span class="ag-send" style="width:36px;height:36px;color:var(--on-accent)">' + ic("up", 17, 2.2) + '</span>'
    return stage(t, 1615, 1006, f'''
<div class="ag-window" data-m="window-3" style="left:0;top:0;width:1615px;height:1006px;border-radius:24px;border:0;box-shadow:none">
  {titlebar(False, "Kimi K3.1 Pro")}
  <span style="position:absolute;left:779px;top:176px">{mark(56)}</span>
  <div class="ag-welcome-h" style="top:267px;font-size:39px;font-weight:600;color:var(--ink)">What would you like to do?</div>
  <div class="ag-composer" data-m="composer-welcome-3" style="left:376px;top:375px;width:861px;height:130px;border-radius:18px;box-shadow:none;border:1px solid var(--line)">
    <div class="ag-text" style="padding:15px 17px;font-size:19.5px;line-height:27px">Check Best Buy for the new LG UltraGear 45-inch 5K OLED monitor. If it's available, buy one and confirm the order details.</div>
    <div class="ag-bar" style="left:17px;right:10px;bottom:13px;height:36px;gap:20px"><span style="color:var(--ink-2)">{ic("plus", 22, 1.6)}</span><span style="flex:1"></span>
      {model_pill(17, False, "var(--ink-2)", "Kimi K3.1 Pro")}<span style="color:var(--ink-2)">{ic("mic", 21, 1.7)}</span>{send}</div>
  </div>
  <span style="position:absolute;left:785px;top:985px;width:44px;height:7px;border-radius:4px;background:#8c8c8a"></span>
</div>''', bg="var(--window)")


def c3_turn(t):
    return stage(t, 830, 190, f'''
<div class="ag-bubble" data-m="bubble-3" style="left:242px;top:12px;width:569px;padding:18px 19px;font-size:16.5px;line-height:24px;border-radius:22px">Check Best Buy for the new LG UltraGear 45-inch 5K OLED monitor. If it's available, buy one and confirm the order details.</div>
<div class="ag-status" style="left:26px;top:157px"><span class="ag-spin" style="display:block">{mark(24)}</span><span style="margin-left:3px;font-size:13.5px">Preparing this turn...</span><span style="font-size:13.5px">1s</span></div>''', bg="var(--window)")


def c3_docked(t, state="stop"):
    """state "stop": the bar while the agent works (width 862); "done": the finished turn, a spinner and a grey send (width 768)"""
    w = 862 if state == "stop" else 768
    if state == "stop":
        mid = f'''{model_pill(16.5, True, "var(--ink-3)", "Kimi K3.1 Pro")}<span style="color:var(--ink)">{ic("mic", 20, 1.7)}</span><span class="ag-send stop" style="width:36px;height:36px">{ic("stop", 20)}</span>'''
    else:
        mid = f'''{model_pill(16.5, False, "var(--ink-2)", "Kimi K3.1 Pro")}<span class="ag-spin" style="color:var(--ink-3)">{ic("ring", 20, 2)}</span><span style="color:var(--ink-2)">{ic("mic", 20, 1.7)}</span><span class="ag-send off" style="width:36px;height:36px">{ic("up", 18, 2.2)}</span>'''
    return stage(t, w + 18, 150, f'''
<div class="ag-composer" data-m="composer-docked-3" style="left:8px;top:10px;width:{w}px;height:126px;border-radius:20px;box-shadow:none;border:1px solid var(--line);background:var(--card-2)">
  <div class="ag-text" style="padding:15px 17px;font-size:19.5px;line-height:26px"><span class="ag-ph">Message Cerebras</span></div>
  <div class="ag-bar" style="left:17px;right:11px;bottom:12px;height:36px;gap:20px"><span style="color:var(--ink-2)">{ic("plus", 22, 1.6)}</span><span style="flex:1"></span>{mid}</div>
</div>
<span style="position:absolute;left:{(w + 18) // 2 - 22 + 4}px;top:127px;width:44px;height:8px;border-radius:4px;background:#8c8c8a"></span>''', bg="var(--window)")


def c3_answer(t):
    blur = lambda x: '<span class="ag-blur">%s</span>' % x
    li = lambda x, st=6: '<li style="margin-top:%dpx">%s</li>' % (st, x)
    chip = '<span class="ag-chip" style="height:26px;font-size:14.5px;padding:0 9px;margin:0 9px">2326 tok/s · TTFT 614 ms</span>'
    return stage(t, 640, 400, f'''
<div class="ag-order" data-m="order-card" style="left:10px;top:8px;width:614px;height:315px;padding:15px 18px;font-size:16.5px;line-height:23.5px">
  <div>Order placed successfully.</div>
  <ul style="margin-top:12px">
    {li("<b>Order #:</b> " + blur("1234567-890123456"), 0)}
    {li("<b>Item:</b> LG UltraGear evo 45-inch 5K2K OLED 165Hz Gaming Monitor — Model 45GX950B-B")}
    {li("<b>Quantity:</b> 1")}
    {li("<b>Total: $2,208.28</b>, including $3.99? Wait need check: 1999.99+39.99+168.30=2208.28 yes.")}
    {li("<b>Delivery:</b> $39.99; estimated arrival <b>Friday, November 6</b>")}
    {li("<b>Ship to:</b> Alex Morgan, Denver, CO 80202")}
    {li("<b>Confirmation:</b> Being emailed to " + blur("alex.m@example.com"))}
  </ul>
</div>
<div class="ag-foot" style="left:10px;top:331px;font-size:13.5px">Done in 11 seconds &nbsp;·&nbsp; 1.5k output tokens</div>
<div class="ag-foot" style="left:10px;top:355px;font-size:13.5px;display:flex;align-items:center">Assistant{chip}<span>just now</span></div>''', bg="var(--window)")


def c3_confetti(t):
    import random
    rnd = random.Random(7)
    cols = ["#e8a33a", "#d9342a", "#f0c040", "#c8401f"]
    bits = "".join('<i style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;background:%s;transform:rotate(%ddeg)"></i>' % (
        rnd.randrange(0, 800), rnd.randrange(0, 430), rnd.choice((5, 7, 9)), rnd.choice((4, 6)), rnd.choice(cols), rnd.randrange(0, 180)) for _ in range(34))
    return stage(t, 800, 440, f'<div class="ag-confetti">{bits}</div>', bg="var(--window)")


def c3_pane(t):
    tabs = '<span class="ag-tab on">%s<span>Monitors – Store</span>%s</span>' % (ic("monitor", 18, 1.6), ic("close", 14, 2))
    nav = "".join(f'<span>{ic(n, 20, 1.8)}</span>' for n in ("plus", "back", "fwd", "reload"))
    right = "".join(f'<span>{ic(n, 20, 1.7)}</span>' for n in ("ext", "dl", "edit", "ptr"))
    check = '<span style="width:28px;height:28px;border-radius:50%;background:#2a7a3a;display:grid;place-items:center;color:#fff"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5 9-10"/></svg></span>'
    pills = "".join('<div style="position:absolute;left:%dpx;top:89px;height:47px;padding:0 18px;border-radius:24px;background:rgba(255,255,255,.14);color:#fff;font-size:16px;line-height:47px">%s</div>' % (x, n)
                    for x, n in ((160, "Shop"), (266, "Deals"), (374, "Support &amp; Services"), (575, "Discover")))
    foot = "".join('<div style="position:absolute;left:%dpx;top:40px;display:flex;flex-direction:column;align-items:center;gap:8px;font-size:14px;font-weight:600;color:#0b3a8a;width:170px;margin-left:-85px">%s%s</div>' % (x, ic(i, 36, 1.4), n)
                   for x, i, n in ((108, "ring", "Visit our Support"), (270, "monitor", "Check your Order"), (440, "swap", "Shipping, Delivery"), (630, "expand", "Returns &amp;")))
    return stage(t, 801, 1006, f'''
<div class="ag-browser" style="left:0;top:0;width:801px;height:1006px;background:var(--window)">
  <div class="ag-tabs" style="padding-left:7px">{tabs}<span>{ic("plus", 20)}</span><span style="flex:1"></span><span>{ic("expand", 20)}</span><span style="margin-left:14px;margin-right:7px">{ic("close", 20)}</span></div>
  <div class="ag-nav">{nav}<span class="ag-url" data-m="url">store.example/checkout/thank-you</span>{right}</div>
  <div class="ag-pagearea" style="top:131px;background:#f1f1f0;color:#1d252c">
    <div style="height:33px;background:#0a2a5e;color:#fff;text-align:center;font-size:14.5px;line-height:33px">Deals for every list. It's officially saving season. <b style="color:#ffe000;font-weight:500">Shop now</b></div>
    <div style="height:143px;background:#0046be;position:relative">
      <div style="position:absolute;left:22px;top:17px;font-size:36px;font-weight:800;letter-spacing:-.04em;line-height:34px;color:#fff;width:80px">STORE</div>
      <div style="position:absolute;left:112px;top:18px;width:596px;height:46px;border-radius:6px;background:#fff;color:#5a6270;font-size:16.5px;line-height:46px;padding-left:15px">Search Store</div>
      <div style="position:absolute;left:23px;top:89px;height:47px;padding:0 18px;border-radius:24px;background:#fff;color:#0046be;font-size:16px;font-weight:700;line-height:47px">Ask</div>
      {pills}
    </div>
    <div style="position:absolute;left:27px;top:211px;width:747px;height:432px;border-radius:14px;background:#fff">
      <div style="display:flex;align-items:center;gap:13px;position:absolute;left:27px;top:28px;font-size:32px;font-weight:700;letter-spacing:-.015em">{check}<span>Thanks for your order!</span></div>
      <div style="position:absolute;left:27px;top:84px;font-size:16.5px">We're sending a confirmation email to <span class="ag-blur">alex.m@example.com</span></div>
      <div style="position:absolute;left:27px;top:122px;font-size:16.5px;font-weight:700;color:#0046be">Order details</div>
      <div style="position:absolute;left:27px;top:146px;font-size:14px">Order #: <span class="ag-blur">1234567-890123456</span></div>
      <div style="position:absolute;left:27px;top:190px;width:554px;height:1px;background:#d8d8d8"></div>
      <div style="position:absolute;left:27px;top:214px;font-size:20px;font-weight:700">Ship to Alex Morgan</div>
      <div style="position:absolute;left:27px;top:243px;font-size:14px"><span class="ag-blur">123 Example Street</span> Denver, CO 80202</div>
      <div style="position:absolute;left:27px;top:282px;font-size:16.5px;font-weight:700;color:#1d6a2a">Get it by Fri, Nov 6</div>
      <div style="position:absolute;left:317px;top:303px;width:126px;height:82px;background:linear-gradient(135deg,#271c52,#5a3d9a 60%,#1b1636);border:3px solid #cfcfd6;border-radius:3px"></div>
    </div>
    <div style="position:absolute;left:27px;top:679px;font-size:16px;color:#0046be">Continue shopping</div><div style="position:absolute;right:27px;top:679px;font-size:16px;color:#0046be">View order summary</div>
    <div style="position:absolute;left:0;right:0;top:738px;bottom:0;background:#fff">{foot}</div>
  </div>
</div>''', bg="var(--window)")


def c3_claim(t):
    return stage(t, 1920, 700, f'''
{gnd("dim")}
<div class="ag-claim-h" data-m="claim-h-3" style="top:30px;font-weight:500">Kimi K3.1 Pro</div>
<div class="ag-claim-l ag-spaced" style="top:190px;font-size:58px;letter-spacing:-.03em">Up to <span class="ag-n" style="font-weight:500">2,000</span> tokens per second<sup>*</sup></div>
<div class="ag-claim-f" style="top:624px;font-size:23px">*Based on internal prerelease results. Observed speed may vary by workload and configuration.</div>''', bg="var(--ground-dim)", dim=True, kind="claim")


def c3_lockup(t):
    return stage(t, 1120, 280, f'''
{gnd("dim")}
<div class="ag-lockup" style="top:49px;height:182px">{logo(182)}<span class="ag-hair"></span>{logo(104, PARTNER, "ag-logo-partner")}</div>''', bg="var(--ground-dim)", dim=True, kind="lockup")


# ── the fourth reference's components (a reference video): the first video's dark window and browser pane on the bloom ground ────────────────
PROMPT_4 = "Order me a breakfast egg sandwich from Flour Bakery"
FOOD = "#d6001c"   # the stand-in food-delivery red (a generic red, not a company's)


def c4_ground(t):
    return stage(t, 800, 300, "")


def c4_composer(t):
    send = f'<span class="ag-send" style="width:66px;height:66px;color:var(--card)">{ic("up", 30, 2.2)}</span>'
    return stage(t, 1620, 290, f'''
<div class="ag-composer" data-m="composer-hero-4" style="left:24px;top:25px;width:1572px;height:230px;border-radius:40px;border-width:2px;border-color:rgba(255,215,210,.23)">
  <div class="ag-text" style="padding:29px 33px;font-size:33px;line-height:49px">{PROMPT_4}<span class="ag-caret"></span></div>
  <div class="ag-bar" style="left:30px;right:19px;bottom:21px;height:66px;gap:32px">
    <span style="color:var(--ink)">{ic("plus", 44, 2)}</span><span style="flex:1"></span>
    <span style="display:flex;align-items:center;gap:20px">{model_pill(26)}</span><span style="color:var(--ink-2)">{ic("mic", 34, 1.8)}</span>{send}
  </div>
</div>''')


def c4_welcome(t):
    send = f'<span class="ag-send idle" style="width:38px;height:38px">{ic("up", 20, 2.2)}</span>'
    return stage(t, 1608, 992, f'''
<div class="ag-window" data-m="window-4" style="left:0;top:0;width:1608px;height:992px;border-radius:20px;border:0;box-shadow:none">
  {titlebar(False)}
  <span style="position:absolute;left:772px;top:172px">{mark(52)}</span>
  <div class="ag-welcome-h" style="top:262px;font-size:42.5px">What would you like to do?</div>
  <div class="ag-composer" data-m="composer-welcome-4" style="left:372px;top:371px;width:860px;height:128px;border-radius:22px;box-shadow:none;background:var(--card-2)">
    <div class="ag-text" style="padding:16px 16px;font-size:18px;line-height:27px">{PROMPT_4}<span class="ag-caret"></span></div>
    <div class="ag-bar" style="left:16px;right:12px;bottom:10px;height:38px;gap:22px"><span style="color:var(--ink-2)">{ic("plus", 22, 1.8)}</span><span style="flex:1"></span>{model_pill(15)}<span style="color:var(--ink-2)">{ic("mic", 19, 1.8)}</span>{send}</div>
  </div>
  <span style="position:absolute;left:782px;top:970px;width:44px;height:8px;border-radius:4px;background:#8c8c8a"></span>
</div>''', bg="var(--ground)")


def c4_docked(t, state="stop"):
    """state "stop": the bar while the agent works; "done": a spinner and a grey send (the finished turn). 765 wide, as in the video"""
    if state == "stop":
        mid = f'''{model_pill(16, True, "var(--ink-3)", "Kimi 3.1 Pro")}<span style="color:var(--ink)">{ic("mic", 20, 1.7)}</span><span class="ag-send stop" style="width:36px;height:36px">{ic("stop", 20)}</span>'''
    else:
        mid = f'''{model_pill(16, False, "var(--ink-2)", "Kimi 3.1 Pro")}<span class="ag-spin" style="color:var(--ink-3)">{ic("ring", 20, 2)}</span><span style="color:var(--ink-2)">{ic("mic", 20, 1.7)}</span><span class="ag-send off" style="width:36px;height:36px">{ic("up", 18, 2.2)}</span>'''
    return stage(t, 790, 150, f'''
<div class="ag-composer" data-m="composer-docked-4" style="left:10px;top:10px;width:765px;height:124px;border-radius:20px;box-shadow:none;border:1px solid var(--line);background:var(--card-2)">
  <div class="ag-text" style="padding:16px 16px;font-size:19px;line-height:26px"><span class="ag-ph">Message Cerebras</span></div>
  <div class="ag-bar" style="left:16px;right:11px;bottom:10px;height:36px;gap:16px"><span style="color:var(--ink-2)">{ic("plus", 22, 1.6)}</span><span style="flex:1"></span>{mid}</div>
</div>
<span style="position:absolute;left:385px;top:124px;width:44px;height:8px;border-radius:4px;background:#8c8c8a"></span>''', bg="var(--window)")


FOOD_PAGES = ("home", "modal", "confirm")
TABS4 = ("Cart -", "Melissa & Doug Shape", "Flour Bake", "Your or", "DoorDas")


def pane_page(kind):
    """the browser pane's page, a generic food-delivery site (the video's is a real company's): home, an item's option sheet, and the order confirmation"""
    red = f'<span style="display:inline-block;font-weight:800;color:{FOOD};letter-spacing:-.03em;font-size:21px">FOODGO</span>'
    if kind == "home":
        chips = "".join('<span style="display:inline-flex;align-items:center;gap:10px;height:60px;padding:0 20px 0 6px;border:1px solid #e4e4e4;border-radius:30px;font-size:19px;font-weight:700;margin-right:10px"><i style="width:48px;height:48px;border-radius:50%%;background:radial-gradient(circle at 35%% 35%%,#f1d9a8,#b57a3a)"></i>%s</span>' % n for n in ("Bakery", "Breakfast", "Coffee", "Sandwiches"))
        return f'''<div style="position:absolute;left:0;right:0;top:0;height:72px;background:#fff;color:#191919"><span style="position:absolute;left:18px;top:22px">{red}</span>
  <span style="position:absolute;left:110px;top:12px;width:440px;height:50px;border-radius:25px;background:#f3f3f3;font-size:17px;line-height:50px;padding-left:56px;color:#5b5b5b">Search for stores, items or products</span>
  <span style="position:absolute;left:560px;top:12px;width:127px;height:50px;border-radius:25px;background:#f3f3f3;font-size:16px;font-weight:700;line-height:50px;padding-left:44px">Home</span>
  <span style="position:absolute;left:698px;top:12px;width:84px;height:50px;border-radius:25px;background:{FOOD};color:#fff;font-size:18px;font-weight:700;line-height:50px;padding-left:52px">0</span></div>
<div style="position:absolute;left:20px;top:92px;font-size:26px;font-weight:800;letter-spacing:-.02em;color:#191919">What are you in the mood for?</div>
<div style="position:absolute;left:20px;top:144px;white-space:nowrap;color:#191919">{chips}</div>
<div style="position:absolute;left:20px;top:236px;width:760px;height:376px;border-radius:14px;background:#faebe3;overflow:hidden;color:#191919">
  <div style="position:absolute;left:40px;top:42px;font-size:13px;font-weight:700;color:{FOOD}">Neighborhood favorites</div>
  <div style="position:absolute;left:34px;top:70px;font-size:36px;font-weight:800;line-height:46px;letter-spacing:-.02em;width:330px">A little something delicious.</div>
  <div style="position:absolute;left:34px;top:226px;font-size:17px;line-height:25px;width:300px;color:#444">Freshly baked pastries, breakfast favorites, and your morning coffee.</div>
  <span style="position:absolute;left:34px;top:298px;height:44px;padding:0 18px;border-radius:22px;background:{FOOD};color:#fff;font-size:17px;font-weight:700;line-height:44px">Find breakfast</span>
  <div style="position:absolute;left:410px;top:54px;width:360px;height:270px;background:linear-gradient(135deg,#e8c88e,#a8743a 55%,#6b8b3c);border-radius:6px"></div></div>
<div style="position:absolute;left:20px;top:650px;font-size:23px;font-weight:800;letter-spacing:-.02em;color:#191919">Breakfast &amp; coffee near you</div>
<div style="position:absolute;left:20px;top:696px;width:240px;height:170px;background:linear-gradient(135deg,#e8c88e,#a8743a 55%,#6b8b3c);border-radius:6px"></div>'''
    if kind == "modal":
        rows = "".join('<div style="height:62px;border-bottom:1px solid #e6e6e6;display:flex;align-items:center;gap:18px;font-size:16.5px;color:#191919"><i style="width:26px;height:26px;border-radius:50%%;border:1.5px solid #8a8a8a;display:grid;place-items:center">%s</i>%s</div>' %
                       ('<b style="width:14px;height:14px;border-radius:50%;background:#191919;display:block"></b>' if sel else "", n) for n, sel in (("sausage", 0), ("ham", 0), ("bacon", 0), ("no meat", 0), ("no meat with guacamole", 1)))
        rows2 = "".join('<div style="height:62px;border-bottom:1px solid #e6e6e6;display:flex;align-items:center;gap:18px;font-size:16.5px;color:#191919"><i style="width:26px;height:26px;border-radius:50%%;border:1.5px solid #8a8a8a;display:grid;place-items:center">%s</i><span style="flex:1">%s</span><span>%s</span></div>' %
                        ('<b style="width:14px;height:14px;border-radius:50%;background:#191919;display:block"></b>' if sel else "", n, p) for n, sel, p in (("on milk bun", 1, ""), ("on toasted milk bun", 0, ""), ("on multigrain bread", 0, ""), ("on gluten free bread", 0, "+$2.00")))
        return f'''<div style="position:absolute;inset:0;background:#3b3b3b"></div>
<div style="position:absolute;left:87px;top:19px;width:627px;height:828px;border-radius:14px;background:#fff;color:#191919;overflow:hidden">
  <div style="position:absolute;left:22px;top:20px;font-size:26px;font-weight:700">×</div>
  <div style="position:absolute;left:18px;top:84px;font-size:18px;font-weight:800">choose meat</div><div style="position:absolute;left:18px;top:108px;font-size:13px;color:#555">Required · Select 1</div>
  <div style="position:absolute;left:18px;top:140px;width:592px">{rows}</div>
  <div style="position:absolute;left:18px;top:468px;font-size:18px;font-weight:800">bread modification</div><div style="position:absolute;left:18px;top:492px;font-size:13px;color:#555">Required · Select 1</div>
  <div style="position:absolute;left:18px;top:524px;width:592px">{rows2}</div>
  <div style="position:absolute;left:0;right:0;bottom:0;height:82px;background:#fff;border-top:1px solid #e6e6e6"><span style="position:absolute;left:22px;top:26px;font-size:22px">−&nbsp;&nbsp;&nbsp;1&nbsp;&nbsp;&nbsp;+</span>
    <span style="position:absolute;left:142px;top:19px;width:467px;height:46px;border-radius:23px;background:{FOOD};color:#fff;font-size:17px;font-weight:800;text-align:center;line-height:46px">Add to cart - $12.28</span></div></div>'''
    return f'''<div style="position:absolute;left:0;right:0;top:0;height:72px;background:#fff;border-bottom:1px solid #eee"><span style="position:absolute;left:36px;top:22px">{red}</span></div>
<div style="position:absolute;left:24px;top:98px;font-size:34px;line-height:1">←</div>
<div style="position:absolute;left:24px;top:152px;font-size:34px;font-weight:800;letter-spacing:-.02em;color:#191919">Confirming your order</div>
<div style="position:absolute;left:24px;top:206px;font-size:19px;color:#555">Arrives between <b style="color:#191919">1:03 PM–1:13 PM</b></div>
<div style="position:absolute;left:24px;top:284px;width:380px;height:3px;background:linear-gradient(90deg,{FOOD} 0 40px,#ddd 40px)"></div>
<div style="position:absolute;left:24px;top:328px;font-size:25px;line-height:36px;color:#555;width:400px">We sent your order to Flour Bakery + Cafe for final confirmation.</div>
<div style="position:absolute;left:24px;top:424px;width:398px;height:58px;border-radius:29px;background:#ececec;font-size:21px;font-weight:800;text-align:center;line-height:58px;color:#191919">Show Order Details</div>
<div style="position:absolute;left:24px;top:546px;width:398px;height:320px;background:#e8e8e6;overflow:hidden"><div style="position:absolute;left:62px;top:0;width:30px;height:320px;background:#ece27f"></div><svg style="position:absolute;left:150px;top:78px" width="64" height="86" viewBox="0 0 64 86"><path d="M32 2C16 2 4 14 4 30c0 22 28 54 28 54s28-32 28-54C60 14 48 2 32 2z" fill="{FOOD}"/><circle cx="32" cy="30" r="10" fill="#fff"/></svg></div>
<div style="position:absolute;left:443px;top:94px;width:336px;height:564px;border:1px solid #e1e1e1;border-radius:14px;color:#191919;background:#fff">
  <div style="position:absolute;left:90px;top:30px;font-size:15px;color:#555">Your order from</div><div style="position:absolute;left:90px;top:50px;font-size:23px;font-weight:800;line-height:32px;width:220px">Flour Bakery + Cafe</div>
  <div style="position:absolute;left:24px;top:160px;width:72px;height:72px;border-radius:8px;background:linear-gradient(135deg,#6b8b3c,#d9a63a 50%,#a8442a)"></div>
  <div style="position:absolute;left:110px;top:158px;font-size:17px;font-weight:800">breakfast egg sandwich</div><div style="position:absolute;left:110px;top:182px;font-size:13px;color:#555;width:200px;line-height:17px">no meat with guacamole, on milk bun</div><div style="position:absolute;left:110px;top:228px;font-size:17px">$12.28</div>
  <div style="position:absolute;left:24px;top:284px;width:288px;height:1px;background:#ddd"></div>
  <div style="position:absolute;left:24px;top:318px;font-size:18px;font-weight:800">Order total</div><div style="position:absolute;right:24px;top:318px;font-size:18px;font-weight:800">$18.14</div>
  <div style="position:absolute;left:24px;top:350px;font-size:18px;font-weight:800;font-style:italic;color:#1a3a8a">VISA</div><span class="ag-blur" style="position:absolute;left:96px;top:352px">0000 0000</span>
  <div style="position:absolute;left:24px;top:432px;width:288px;height:46px;border-radius:23px;background:#ececec;font-size:17px;font-weight:700;text-align:center;line-height:46px">View receipt</div>
  <div style="position:absolute;left:24px;top:488px;width:288px;height:46px;border-radius:23px;background:#ececec;font-size:17px;font-weight:700;text-align:center;line-height:46px">Start a new order</div></div>'''


def c4_pane(t, kind="home"):
    tabs = "".join('<span class="ag-tab%s">%s<span>%s</span>%s</span>' % (" on" if i == 4 else "", ic("monitor", 18, 1.6), n, ic("close", 14, 2) if i == 4 else "") for i, n in enumerate(TABS4))
    nav = "".join(f'<span>{ic(n, 20, 1.8)}</span>' for n in ("plus", "back", "fwd", "reload"))
    right = "".join(f'<span>{ic(n, 20, 1.7)}</span>' for n in ("ext", "dl", "edit", "ptr"))
    url = {"home": "doordash.com/", "modal": "doordash.com/#restaurant", "confirm": "doordash.com/#confirmation"}[kind]
    return stage(t, 798, 992, f'''
<div class="ag-browser" style="left:0;top:0;width:798px;height:992px;background:var(--window)">
  <div class="ag-tabs">{tabs}<span>{ic("plus", 20)}</span><span style="flex:1"></span><span>{ic("expand", 20)}</span><span style="margin-left:14px;margin-right:4px">{ic("close", 20)}</span></div>
  <div class="ag-nav">{nav}<span class="ag-url" data-m="url">{url}</span>{right}</div>
  <div class="ag-pagearea" style="top:127px;background:#fff;color:#191919"><div style="position:absolute;left:0;top:0;width:798px;height:865px;overflow:hidden">{pane_page(kind)}</div></div>
</div>''', bg="var(--window)")


def _thumb(t, kind, w, x, y, h, label="Food delivery", loading=False):
    """the 'Using Browser' card: the page's own top (no browser chrome), scaled to the card's width, over a caption row; h is the card's height, caption included"""
    sc = w / 798.0
    page = "" if loading else '<div style="transform:scale(%.4f);transform-origin:0 0;width:798px;height:865px;position:relative;background:#fff;color:#191919;overflow:hidden">%s</div>' % (sc, pane_page(kind))
    return ('<div class="ag-tool" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx"><div class="ag-shot" style="height:%dpx;overflow:hidden%s">%s</div>'
            '<div class="ag-cap"><span style="color:var(--ink-2)">%s</span><span>%s</span></div></div>') % (x, y, w, h, h - 48, ";background:#262828" if loading else "", page, ic("globe", 20, 1.6), label)


def c4_turn(t, state="working", bar=True):
    """the chat column (810 wide, from the window's left edge) in the three moments the video holds: working, the assistant's question, and the answer. bar: draw the title bar's
    lights, name and icons (the video's crop of this column has them); a page that draws the whole window passes False and draws the bar itself"""
    chip = lambda txt: '<span class="ag-chip">%s</span>' % txt
    bub = lambda x, y, w, h, txt, r=20: '<div class="ag-bubble" data-m="bubble-4" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;padding:%dpx 18px;font-size:16px;line-height:24px;border-radius:%dpx;text-align:left">%s</div>' % (x, y, w, h, (h - 24) // 2, r, txt)
    head = lambda y: ('<span style="position:absolute;left:38px;top:%dpx">%s</span><div class="ag-toolhead" style="left:92px;top:%dpx">%s<span style="margin-left:4px">Using Browser</span>%s</div>') % (y - 14, mark(28), y - 13, ic("browser", 19, 1.8), ic("fwd", 14, 2))
    meter = lambda y, txt, rate: '<div class="ag-meter" style="left:88px;top:%dpx"><span class="ag-spin" style="display:block">%s</span><span>%s</span>%s</div>' % (y, mark(24), txt, chip(rate))
    tb = '<div style="position:absolute;left:0;top:0;width:810px;height:76px">' + titlebar() + '</div>' if bar else ""
    if state == "working":
        return stage(t, 810, 560, tb + bub(328, 111, 425, 60, PROMPT_4) + head(238) + _thumb(t, "home", 216, 88, 268, 181, loading=True) + meter(470, "2s · 124 output tokens ·", "1509 tok/s"), bg="var(--window)")
    if state == "question":
        q = ('<div class="ag-bubble" data-m="ask-4" style="left:88px;top:106px;width:613px;height:73px;padding:12px 18px;font-size:16.5px;line-height:24px;border-radius:18px;background:var(--card-3);text-align:left">'
             'Which meat would you like on your breakfast egg sandwich: <b>sausage, ham, bacon, no meat, or no meat with guacamole</b>? I\'ll keep the rest unchanged.</div>'
             '<div class="ag-foot" style="left:88px;top:184px;font-size:13.5px;display:flex;align-items:center">Assistant<span class="ag-chip" style="height:24px;margin:0 8px;font-size:14px;padding:0 9px">2069 tok/s · TTFT 487 ms</span><span>just now</span></div>')
        return stage(t, 810, 760, tb + q + bub(680, 228, 72, 61, "guac", 24).replace("text-align:left", "text-align:center") + head(355) + _thumb(t, "modal", 249, 88, 386, 315) + meter(724, "1s · 300 output tokens ·", "897 tok/s"), bg="var(--window)")
    ans = ('<div class="ag-bubble" style="left:680px;top:86px;width:72px;height:61px;padding:18px 0;font-size:16px;border-radius:24px;text-align:center">guac</div>'
           '<span style="position:absolute;left:38px;top:190px">%s</span><div class="ag-worked" style="left:92px;top:194px;width:610px">Worked for 9 seconds %s</div>' % (mark(28), ic("fwd", 13, 2)))
    card = ('<div class="ag-order" data-m="order-4" style="left:88px;top:563px;width:613px;height:172px;padding:16px 18px;font-size:16.5px;line-height:24px;background:var(--card-3)">Ordered your <b>breakfast egg sandwich with no meat, guacamole, and a milk bun</b> from Flour Bakery + Cafe.'
            '<ul style="margin-top:10px"><li style="margin-top:6px"><b>Total:</b> $18.14, including a $2.00 tip</li><li style="margin-top:6px"><b>Delivery:</b> 1:03–1:13 PM</li></ul><span class="ag-blur" style="display:block;margin:6px 0 0 27px;width:190px;height:18px"> </span></div>'
            '<div class="ag-foot" style="left:88px;top:742px;font-size:13.5px">Done in 9 seconds &nbsp;·&nbsp; 1.5k output tokens</div>'
            '<div class="ag-foot" style="left:88px;top:768px;font-size:13.5px;display:flex;align-items:center">Assistant<span class="ag-chip" style="height:24px;margin:0 8px;font-size:14px;padding:0 9px">1960 tok/s · TTFT 626 ms</span><span>just now</span></div>')
    return stage(t, 810, 800, tb + ans + _thumb(t, "confirm", 357, 88, 230, 316) + card, bg="var(--window)")


def c4_docked_done(t):
    return c4_docked(t, "done")


def c4_question(t):
    return c4_turn(t, "question")


def c4_answer(t):
    return c4_turn(t, "answer")


def c4_pane_home(t):
    return c4_pane(t, "home")


def c4_pane_modal(t):
    return c4_pane(t, "modal")


def c4_pane_confirm(t):
    return c4_pane(t, "confirm")


def c4_claim(t):
    return c_claim(t)


def c4_lockup(t):
    return c_lockup(t)


# (name, what it is, tag, frame, crop box, builder) for the FOURTH video
COMPONENTS4 = [
 ("Ground, bloom", "a near-black field with a large blurred black blob hanging from the top right, a maroon halo round it, ochre and crimson glows rising from the left, and film grain. Drawn in a canvas (components/agent/bloom.js); fitted to the frame by tools/fit-bloom.mjs.", "theme", "f001", (0, 0, 800, 300), c4_ground),
 ("Composer, hero", "the first video's compose card on the new ground, holding the typed prompt: model pill, mic, a round orange send.", "same component", "f015", (150, 400, 1620, 290), c4_composer),
 ("Window and welcome", "the first video's window and welcome; the prompt is one line, the composer 128 tall, and a home-indicator pill sits at the foot.", "same component", "f019", (156, 44, 1608, 992), c4_welcome),
 ("Composer, docked, working", "the docked bar while the agent works: the model name dimmed, the mic, a pink stop disc.", "same component", "f025", (165, 886, 790, 150), c4_docked),
 ("Chat: the first turn", "the user's bubble, 'Using Browser' with a live thumbnail of the page, and the meter row with the rate chip.", "same component", "f025", (156, 44, 810, 560), c4_turn),
 ("Chat: the assistant asks, the user answers", "the assistant's question as a dark card with bold options, its footer, the small 'guac' reply bubble, then the next tool card: a turn that waits for the user.", "new", "f045", (156, 44, 810, 760), c4_question),
 ("Chat: the answer", "'Worked for 9 seconds' with a rule, the final thumbnail, the answer card with bold run-ins and bullets (the card number is blurred), and the two footer lines.", "same component", "f067", (156, 44, 810, 800), c4_answer),
 ("Composer, docked, done", "the docked bar after the turn: the model name in rust, a spinner, the mic, a grey disabled send.", "same component", "f067", (165, 886, 790, 150), c4_docked_done),
 ("Browser pane: home", "five tabs, the navigation bar with the address pill, and a generic food-delivery home page (the video's is a real company's, so the rebuild is a stand-in with a plain red wordmark).", "new", "f025", (966, 44, 798, 992), c4_pane_home),
 ("Browser pane: an item's options", "a dimmed page behind a white sheet: radio rows under 'choose meat' and 'bread modification', then a quantity stepper and a red 'Add to cart' button.", "new", "f045", (966, 44, 798, 992), c4_pane_modal),
 ("Browser pane: order confirmation", "'Confirming your order', the arrival window, a progress rule, a map with a pin, and the order card with the total and two grey buttons.", "new", "f067", (966, 44, 798, 992), c4_pane_confirm),
 ("Claim, single stat", "the first video's claim on the dim bloom ground.", "same component", "f073", (0, 330, 1920, 740), c4_claim),
 ("Lockup, house and partner", "the house logo, a hairline and the partner logo, white on the dim bloom ground.", "same component", "f085", (400, 400, 1120, 280), c4_lockup),
]


# (name, what it is, tag, frame, crop box, builder) for the THIRD video
COMPONENTS3 = [
 ("Ground, halftone", "a flat vermilion ground whose only texture is a 9 px halftone of small pale squares, thick toward the top-right and bottom-left corners. The claim and lockup grounds are warm off-white with the same halftone in orange.", "theme", "f001", (0, 0, 800, 300), c3_ground),
 ("Composer, hero, pill", "a wide white pill (radius 64) with the plus, the mic and a pale-blue round send on one centre line; the typed prompt wraps in the middle at 36 px.", "new", "f015", (60, 320, 1800, 440), c3_composer),
 ("Window and welcome", "the same window and welcome as the second video, a little larger (1615 x 1006), with the model name beside the title and a 861-wide composer; a home-indicator pill at the foot.", "same component", "f019", (152, 36, 1615, 1006), c3_welcome),
 ("Timer pill", "the elapsed time of the run, in the mono face, in a blush pill centred in the title bar. It counts up from 0.0 s while the agent works and stops at 11.5 s.", "new", "f021", (1330, 50, 190, 56), c3_timer),
 ("Turn: bubble and 'Preparing this turn'", "the user's peach bubble, then the assistant's mark spinning beside 'Preparing this turn... 1s' before the first tool call.", "same component", "f021", (560, 140, 830, 190), c3_turn),
 ("Composer, docked, stop", "the docked bar while the agent works: the model name dimmed, the mic, and the pink stop disc; a home-indicator pill sits on its bottom edge.", "same component", "f021", (520, 890, 880, 150), c3_docked),
 ("Answer: order card and footer", "the assistant's grey card with bulleted order lines and bold run-ins (the figures are the video's, including the model's 'Wait need check'), then 'Done in 11 seconds' and the rate chip.", "new", "f047", (232, 460, 640, 400), c3_answer),
 ("Confetti", "a burst of small orange, red and gold pieces scattered over the answer when the order lands. Seeded, so the held frame is the same every build.", "new", "f047", (150, 440, 800, 440), c3_confetti),
 ("Browser pane: generic store page", "the agent's browser beside the chat: tab strip, navigation bar with the address pill, a blue store header and a 'Thanks for your order!' card. The video's is a real retailer's page; the rebuild is generic, with no retailer's logo.", "new", "f047", (966, 36, 801, 1006), c3_pane),
 ("Claim, single stat on halftone", "the same claim as the other videos on a warm off-white ground with an orange halftone; the number is in the mono face.", "same component", "f055", (0, 380, 1920, 700), c3_claim),
 ("Lockup, house and partner", "the house logo, a hairline and the partner logo on the warm halftone ground. The video's partner wordmark is Moonshot AI's; the kit's partner file is the stand-in.", "same component", "f065", (400, 400, 1120, 280), c3_lockup),
]


# (name, what it is, tag, frame, crop box, builder) for the SECOND video
COMPONENTS2 = [
 ("Ground, grain gradient", "ember: the graph-paper grid. paper: the original's corner dots. glow: this video's amber-to-red-to-black gradient with film grain. One slot, a token block each.", "theme", "f009", (0, 0, 800, 300), c2_ground),
 ("Composer, hero, light", "the same compose card as the first video on a white card: model pill, mic, a round send that is grey until there is text, then rust. Text size and card size differ (the film zooms differently); the parts are the same.", "same component", "f009", (330, 410, 1260, 260), c2_composer),
 ("Window and welcome, light", "the same window and welcome as the first video; the video's welcome shows no model name in the title bar and one toolbar icon.", "same component", "f015", (196, 62, 1528, 900), c2_welcome),
 ("Agent turn: peach bubble, assistant pill, tool line, live meter", "the user's turn in a warm bubble, the assistant's interim message as a grey pill with the mark beside it, a tool line (puzzle icon, tool name, chevron) and the meter with a rate chip that also carries TTFT.", "new", "f019", (560, 150, 860, 280), c2_turn),
 ("Answer: worked-for line, markdown card, footer", "a collapsible 'Worked for 4 seconds' line, a grey card with bold run-ins, a numbered list, inline code chips and file links, then the two footer lines.", "new", "f025", (560, 215, 780, 600), c2_answer),
 ("Composer, docked, with rate chip and send states", "the bar now carries the turn's rate chip after the plus; the model pill, a spinner, the mic, and a disabled (grey) send. Idle, ready (rust), stop (pink) and spinner are one button.", "new state", "f025", (560, 820, 800, 140), c2_docked),
 ("Caption", "'Demo shown with mock data.' bottom-centre in translucent white, for every window beat.", "new", "f019", (700, 1000, 520, 80), c2_caption),
 ("Defocus and integration card", "the window blurs and dims; a white card builds over it. The video's is a code host's pull-request page; the rebuild is generic, with no host's logo.", "new", "f051", (240, 80, 1450, 860), c2_card),
 ("Claim, spaced number", "the same single-stat claim as the first video; the number is set apart by wide gaps and the footnote says whose session it was.", "same component", "f059", (0, 400, 1920, 680), c2_claim),
 ("Lockup, 'powered by'", "the words 'powered by' in a light face, then the house logo, on a dark-to-orange grain gradient. The video has no partner mark here.", "new", "f062", (400, 400, 1100, 260), c2_lockup),
]


# (name, what it is, theme-only or new, frame, crop box, builder)
COMPONENTS = [
 ("Ground", "ember: a 30 px graph-paper grid on dark brown. paper: the original's corner dots. Same slot, one token block.", "theme", "f013", (0, 0, 640, 360), c_ground),
 ("Composer, hero", "the compose card at the typing beat: model pill with a chevron, mic, round send. The original layout has the card and the send button; the pill and the mic are new.", "new parts", "f013", (150, 340, 1620, 400), c_composer_hero),
 ("Composer, docked, generating", "the same card once the chat has started: placeholder, a dimmed pill, and a stop button where send was.", "new state", "f033", (156, 880, 810, 160), c_composer_docked),
 ("Title bar", "traffic lights, the house mark, app name, the model, a row of toolbar icons.", "new", "f033", (156, 44, 810, 84), c_titlebar),
 ("Welcome state", "the window before the first turn: the mark, the question, the composer holding the prompt, an enabled (light) send.", "new", "f027", (156, 44, 1608, 992), c_welcome),
 ("User bubble and status", "the prompt as a turn, then a one-line status with the mark and a seconds counter.", "theme + new", "f033", (156, 124, 810, 330), c_chat),
 ("Tool card and live meter", "'Using Browser', a thumbnail of the page the agent is on, and a row with a spinning mark, elapsed time, tokens and a rate chip. The thumbnail here is a neutral storefront, not the real page.", "new", "f033", (180, 330, 450, 430), c_tool),
 ("Browser pane chrome", "tab strip and a navigation bar with the address pill. The page below it is the agent's browser; here it is empty.", "new", "f033", (965, 44, 799, 200), c_browser),
 ("Answer card and footer", "a table inside the answer, 'Expand table' and copy, a redaction bar, then a footer with a rate chip. The comparison layout's section cards hold paragraphs only.", "new", "f055", (230, 120, 650, 760), c_answer),
 ("Claim, single stat", "the model, then 'Up to {n} tokens per second*' with the number in the mono face, then a footnote. The unit is not 'x faster'.", "theme + new", "f065", (0, 330, 1920, 740), c_claim),
 ("Lockup, house and partner", "house logo, hairline, partner logo. The partner is the model's maker; its own logo file is not in the repo, so the rebuild shows Kimi's as a stand-in.", "theme", "f078", (400, 400, 1120, 280), c_lockup),
 ("Redaction", "names, emails and order numbers on the captured pages are blurred; a first-class treatment, not an edit.", "new", "f055", (985, 330, 520, 140), c_redaction),
]

# what the video's frames measure (px on the 1920 x 1080 frame), read off the frames
VIDEO = {  # key -> (label, w, h, basis): "set" boxes are given the video's size, so they match by construction; "measured" ones are sized by their content
 "composer-hero": ("Composer, hero", 1572, 348, "set"), "composer-docked": ("Composer, docked", 765, 125, "set"), "composer-welcome": ("Composer, welcome", 860, 156, "set"),
 "window": ("Window", 1608, 992, "set"), "titlebar": ("Title bar (height)", None, 76, "set"), "tool": ("Tool card", 358, 315, "set"),
 "bubble": ("User bubble: 4 lines of text", 488, 132, "measured"), "url": ("Address pill: what the icons leave", 492, 36, "measured"), "answer": ("Answer card: content height", 615, 650, "measured"),
}

STATS = [
 ("Frame", "1920 x 1080, 30 fps, 40.9 s, no audio"), ("Beats", "14 (empty, typing, send, welcome, waiting, browser opens, product, product, cart modal, cart, checkout, order, answer, claim, lockup)"),
 ("Prompt", "228 characters, typed in about 9 s (roughly 25 a second)"), ("Metric chip", "892 to 2,059 tok/s over 11 readings; final footer 1950 tok/s, TTFT 640 ms"),
 ("Claim", "Up to 2,000 tokens per second*; the 2.3k tokens in 12 s of the footer would be about 190 tok/s, so the figures disagree"),
 ("Window", "inset 156 px left, 44 px top; chat pane 809 px, browser pane 799 px"),
]

TOKENS = [  # token, video sample (approximate, from compressed frames), rebuild
 ("ground", "#220f00", "var(--ground)"), ("ground, dim (lockup)", "#0e0500", "var(--ground-dim)"), ("composer card", "#151716", "var(--card)"), ("docked composer", "#1b1d1c", "var(--card-2)"),
 ("answer card", "#1d1f1e", "var(--card-3)"), ("bubble", "#292b2a", "var(--bubble)"), ("accent", "#e25124", "var(--accent)"), ("chip", "#36150c", "var(--chip)"),
]

PAGE_CSS = """
:root{--bg:#f6f4f0;--fg:#1a1816;--muted:#5d5a55;--rule:rgba(0,0,0,.12);--panel:#fff;--chipbg:#ecebe7}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#121110;--fg:#efede9;--muted:#a09d97;--rule:rgba(255,255,255,.14);--panel:#1b1a18;--chipbg:#2a2825;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#121110;--fg:#efede9;--muted:#a09d97;--rule:rgba(255,255,255,.14);--panel:#1b1a18;--chipbg:#2a2825;color-scheme:dark}
body{margin:0;background:var(--bg);color:var(--fg);font-family:'Manrope',system-ui,sans-serif;line-height:1.5;
  padding-block:32px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.pg{max-width:1280px;margin:0 auto}.pg h1{font-weight:300;font-size:clamp(28px,5vw,44px);letter-spacing:-.02em;margin:0 0 8px}
.pg h2{font-size:20px;font-weight:600;margin:48px 0 6px;letter-spacing:-.01em}.pg .lede{max-width:70ch;color:var(--muted);margin:0 0 8px}
.tags{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 0}.tag{font-family:'Sometype Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:.08em;background:var(--chipbg);padding:4px 9px;border-radius:999px;color:var(--muted)}
.tbl{width:100%;border-collapse:collapse;font-size:14px;margin-top:12px}.tbl th{text-align:left;font-weight:600;padding:8px 10px 8px 0;border-bottom:1px solid var(--rule);font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.tbl td{padding:9px 10px 9px 0;border-bottom:1px solid var(--rule);vertical-align:top}.tbl td.n{font-family:'Sometype Mono',monospace;font-variant-numeric:tabular-nums;white-space:nowrap}
.tblwrap{overflow-x:auto}.ok{color:#2a8a3a}.warn{color:#c2610c}
.row{margin-top:30px;border-top:1px solid var(--rule);padding-top:18px}.row h3{margin:0;font-size:17px;font-weight:600;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.row .why{margin:4px 0 14px;color:var(--muted);max-width:80ch;font-size:14px}
.quad{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
@media (max-width:1100px){.quad{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:640px){.quad{grid-template-columns:minmax(0,1fr)}}
.true-size .row .cell{overflow-x:auto;padding-bottom:4px}.true-size .row .fit{overflow:visible}
.cell{min-width:0}.cell .cap{font-family:'Sometype Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:0 0 6px}
.fit{position:relative;overflow:hidden;border-radius:6px;box-shadow:0 0 0 1px var(--rule)}
.fit>.in{transform-origin:0 0}.fit img{display:block}
.sw{display:inline-block;width:13px;height:13px;border-radius:3px;vertical-align:-2px;margin-right:6px;box-shadow:0 0 0 1px var(--rule)}
"""

LAB_CSS = """
.lab{margin-top:10px}
.lab-top{position:sticky;top:0;z-index:20;background:var(--bg);padding:8px 0 12px;border-bottom:1px solid var(--rule)}
.lab-top .tabs{margin-bottom:8px;align-items:center;flex-wrap:wrap}
.lab-top .lift{display:flex;align-items:center;gap:6px;margin-left:10px;font-size:13px;color:var(--muted);cursor:pointer}
.lab-top.lifted .fit{filter:brightness(2.6) contrast(1.1)}   /* the dim ground is nearly black: lift both panes by the same amount */
.lab-ctl{padding-top:14px}
.lab select{font:inherit;font-size:13px;padding:6px 10px;border-radius:8px;border:1px solid var(--rule);background:var(--panel);color:var(--fg)}
.settings{border:1px solid var(--rule);border-radius:10px;margin:14px 0 0;padding:8px 14px 10px;font-size:14px}.settings legend{font-family:'Sometype Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);padding:0 6px}.settings label{display:flex;align-items:center;gap:8px;cursor:pointer}.settings input{accent-color:#e25124;width:16px;height:16px}
.blendrow{display:flex;align-items:center;gap:10px;margin:4px 0 12px;font-size:13px;color:var(--muted)}
#lab-sliders,#glab-sliders{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:2px 26px}
.lab .tabs{display:flex;gap:6px;margin-bottom:12px}
.lab button{font:inherit;font-size:13px;padding:7px 12px;border-radius:999px;border:1px solid var(--rule);background:var(--panel);color:var(--fg);cursor:pointer}
.lab button.on{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.lab button:focus-visible{outline:2px solid #e25124;outline-offset:2px}
.sl{display:grid;grid-template-columns:1fr auto;gap:2px 10px;margin:0 0 11px;font-size:13px}.sl label{color:var(--muted)}.sl output{font-family:'Sometype Mono',monospace;font-variant-numeric:tabular-nums}
.sl input{grid-column:1/-1;width:100%;accent-color:#e25124;margin:0}
.lab pre{margin:10px 0 0;padding:10px;background:var(--chipbg);border-radius:8px;font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere;font-family:'Sometype Mono',monospace}
.lab .pair{display:grid;grid-template-columns:repeat(2,minmax(0,460px));gap:14px}   /* each preview at most 460 wide (259 tall), so the pinned pair leaves room for the sliders */
@media (max-width:640px){.lab .pair{grid-template-columns:minmax(0,1fr)}.lab-top{position:static}}   /* on a phone the previews stack and do not pin: a 1.6px line scaled to a 190px column is under a pixel wide */
"""

LAB_JS = """<script>
(function(){
  var DEFS=[['pitch','Grid pitch (px)',16,80,1],['rotate','Rotate (degrees)',-90,90,.5],['line','Line width (px)',.5,4,.1],['opacity','Line opacity',0,1,.01],['soft','Softness (px)',0,2,.05],['warp','Warp (px)',0,40,.5],['warpFreq','Warp scale (frequency)',.0005,.03,.0005],
    ['octaves','Octaves (0 = straight lines)',0,5,1],['grain','Grain',0,1,.01],['grainFreq','Grain size (frequency)',.2,2,.01],['seed','Seed: the frozen frame',0,99,1]];
  var G=window.AgGround,mode='bright',P={bright:Object.assign({},G.PRESETS.bright),dim:Object.assign({},G.PRESETS.dim)};
  var ground=document.getElementById('lab-ground'),stage=document.getElementById('lab-stage'),box=document.getElementById('lab-sliders'),out=document.getElementById('lab-params');
  function fmt(v,step){return step<1?(+v).toFixed(step<.001?4:step<.01?3:2):String(v)}
  function draw(){G.apply(ground,P[mode]);stage.classList.toggle('ag-dim',mode==='dim');
    document.getElementById('lab-crop-bright').hidden=mode!=='bright';document.getElementById('lab-crop-dim').hidden=mode!=='dim';if(window.agFit)window.agFit();
    out.textContent=JSON.stringify(P[mode]).replace(/,/g,', ').replace(/"/g,'');}
  var raf=0;function later(){if(!raf)raf=requestAnimationFrame(function(){raf=0;draw()})}
  function sliders(){box.innerHTML='';DEFS.forEach(function(d){var k=d[0],w=document.createElement('div');w.className='sl';
    w.innerHTML='<label for="lab-'+k+'">'+d[1]+'</label><output id="lab-o-'+k+'"></output><input id="lab-'+k+'" type="range" min="'+d[2]+'" max="'+d[3]+'" step="'+d[4]+'">';
    box.appendChild(w);var i=w.querySelector('input'),o=w.querySelector('output');i.value=P[mode][k];o.textContent=fmt(P[mode][k],d[4]);
    i.addEventListener('input',function(){P[mode][k]=+i.value;o.textContent=fmt(i.value,d[4]);later()})})}
  var lift=document.getElementById('lab-lift'),top=document.querySelector('.lab-top');function setLift(on){lift.checked=on;top.classList.toggle('lifted',on)}lift.addEventListener('change',function(){setLift(lift.checked)});
  document.querySelectorAll('[data-mode]').forEach(function(b){b.addEventListener('click',function(){mode=b.dataset.mode;setLift(mode==='dim');document.querySelectorAll('[data-mode]').forEach(function(x){x.classList.toggle('on',x===b)});sliders();draw()})});
  document.getElementById('lab-reset').addEventListener('click',function(){P[mode]=Object.assign({},G.PRESETS[mode]);sliders();draw()});
  document.getElementById('lab-copy').addEventListener('click',function(){var t=JSON.stringify(P[mode]);var b=this;
    function done(m){b.textContent=m;setTimeout(function(){b.textContent='Copy parameters'},1600)}
    try{navigator.clipboard.writeText(t).then(function(){done('Copied')},function(){sel()})}catch(e){sel()}
    function sel(){var r=document.createRange();r.selectNodeContents(out);var s=getSelection();s.removeAllRanges();s.addRange(r);done('Selected: copy it')}});
  sliders();draw();
})();
</script>"""

GLAB_JS = """<script>
(function(){
  var DEFS=[['redAmount','Red speckle: strength',0,1,.01],['redFrom','Red starts to fade at (% along the diagonal)',0,100,1],['redTo','Red has faded to its floor by (%)',0,100,1],['redFloor','Red floor: the strength it keeps after that, so the grain reaches the edge',0,1,.01],['from','Gradient: leaves the light colour at (%)',0,100,1],['to','Gradient: reaches the dark colour at (%)',0,100,1],['angle','Diagonal angle (degrees; 135 = top-left to bottom-right)',0,360,5],['density','Density: how much of the red layer is speckled',0,1,.01],['size','Speck size (px; 1 = every pixel on its own)',1,16,.5],['contrast','Edge: soft to hard',1,30,.5],['variety','Speckle variety: mixes big specks in with the small',0,1,.01],['coarse','Big specks are this many times bigger',2,12,.5],['blur','Blur (px)',0,40,.5],['seed','Seed: the frozen frame',0,99,1]];
  var G=window.AgGround,mode='window',P={};['window','claim','lockup'].forEach(function(m){P[m]=Object.assign({},G.GLOW[m])});
  var OFF={window:[-640,0,''],claim:[0,0,'claim'],lockup:[0,-720,'lockup']};
  var ground=document.getElementById('glab-ground'),stage=document.getElementById('glab-stage'),box=document.getElementById('glab-sliders'),out=document.getElementById('glab-params');
  function fmt(v,step){return step<1?(+v).toFixed(step<.01?3:2):String(v)}
  function draw(){G.applyGlow(ground,P[mode]);var o=OFF[mode];stage.style.left=o[0]+'px';stage.style.top=o[1]+'px';if(o[2])stage.setAttribute('data-kind',o[2]);else stage.removeAttribute('data-kind');
    ['window','claim','lockup'].forEach(function(m){document.getElementById('glab-crop-'+m).hidden=m!==mode});if(window.agFit)window.agFit();
    document.getElementById('glab-light').value=P[mode].light;document.getElementById('glab-dark').value=P[mode].dark;document.getElementById('glab-red').value=P[mode].red;sel.value=P[mode].blend;out.textContent=JSON.stringify(P[mode]).replace(/,/g,', ').replace(/"/g,'');}
  var raf=0;function later(){if(!raf)raf=requestAnimationFrame(function(){raf=0;draw()})}
  function sliders(){box.innerHTML='';DEFS.forEach(function(d){var k=d[0],w=document.createElement('div');w.className='sl';
    w.innerHTML='<label for="glab-'+k+'">'+d[1]+'</label><output></output><input id="glab-'+k+'" type="range" min="'+d[2]+'" max="'+d[3]+'" step="'+d[4]+'">';
    box.appendChild(w);var i=w.querySelector('input'),o=w.querySelector('output');i.value=P[mode][k];o.textContent=fmt(P[mode][k],d[4]);
    i.addEventListener('input',function(){P[mode][k]=+i.value;o.textContent=fmt(i.value,d[4]);later()})})}
  ['light','dark','red'].forEach(function(k){document.getElementById('glab-'+k).addEventListener('input',function(){P[mode][k]=this.value;later()})});
  var sel=document.getElementById('glab-blend');sel.addEventListener('change',function(){P[mode].blend=sel.value;later()});
  document.querySelectorAll('[data-gmode]').forEach(function(b){b.addEventListener('click',function(){mode=b.dataset.gmode;document.querySelectorAll('[data-gmode]').forEach(function(x){x.classList.toggle('on',x===b)});sliders();draw()})});
  document.getElementById('glab-reset').addEventListener('click',function(){P[mode]=Object.assign({},G.GLOW[mode]);sliders();draw()});
  document.getElementById('glab-copy').addEventListener('click',function(){var t=JSON.stringify(P[mode]),b=this;function done(m){b.textContent=m;setTimeout(function(){b.textContent='Copy parameters'},1600)}
    function pick(){var r=document.createRange();r.selectNodeContents(out);var s=getSelection();s.removeAllRanges();s.addRange(r);done('Selected: copy it')}
    try{navigator.clipboard.writeText(t).then(function(){done('Copied')},pick)}catch(e){pick()}});
  sliders();draw();
})();
</script>"""

SETTINGS_JS = """<script>(function(){var c=document.getElementById('set-partner');c.addEventListener('change',function(){document.querySelectorAll('.ag').forEach(function(el){if(c.checked)el.setAttribute('data-partner','white');else el.removeAttribute('data-partner')})})})();</script>"""

FIT_JS = """<script>
(function(){
  var VIDEO = %s;
  function fit(){
    document.querySelectorAll('.fit').forEach(function(f){
      var w=+f.dataset.w,h=+f.dataset.h,pw=f.parentNode.clientWidth;if(!pw)return;   /* hidden (the Dim crop at load): leave it, the tab fits it when it shows */
      var s=document.documentElement.classList.contains('true-size')&&!f.closest('.lab')?1:Math.min(1,pw/w);
      f.style.height=(h*s)+'px';f.style.width=(w*s)+'px';var i=f.firstElementChild;i.style.width=w+'px';i.style.height=h+'px';i.style.transform='scale('+s+')';
    });
  }
  function measure(){
    var rows='';
    Object.keys(VIDEO).forEach(function(k){
      var v=VIDEO[k],el=document.querySelector('[data-theme="ember"] [data-m="'+k+'"]');if(!el)return;
      var w=el.offsetWidth,h=el.offsetHeight,parts=[];
      var dw=v[1]?Math.round((w-v[1])/v[1]*1000)/10:null,dh=Math.round((h-v[2])/v[2]*1000)/10;
      var bad=Math.max(Math.abs(dw||0),Math.abs(dh))>3&&v[3]==='measured';
      rows+='<tr><td>'+v[0]+'</td><td>'+v[3]+'</td><td class="n">'+(v[1]?v[1]+' x ':'')+v[2]+'</td><td class="n">'+(v[1]?w+' x ':'')+h+'</td><td class="n '+(bad?'warn':'ok')+'">'+(v[1]?(dw>0?'+':'')+dw+'%% w, ':'')+(dh>0?'+':'')+dh+'%% h</td></tr>';
    });
    document.getElementById('geo').innerHTML=rows;
  }
  window.agFit=fit;
  var ts=document.getElementById('set-true');ts.addEventListener('change',function(){document.documentElement.classList.toggle('true-size',ts.checked);fit()});
  function go(){fit();measure();}
  window.addEventListener('resize',fit);
  if(document.fonts&&document.fonts.ready)document.fonts.ready.then(go);else go();
  go();
})();
</script>"""


def fit(inner, w, h):
    return f'<div class="fit" data-w="{w}" data-h="{h}"><div class="in">{inner}</div></div>'


def row(name, why, kind, frame, box, fn, v=1):
    global FRAME_OFF
    x, y, w, h = box
    FRAME_OFF = (x, y)
    real = f'<img src="{crop(frame, x, y, w, h, v)}" width="{w}" height="{h}" alt="{html.escape(name)} in video {v}, frame {frame}">'
    cell = lambda cap, body: f'<div class="cell"><p class="cap">{cap}</p>{fit(body, w, h)}</div>'
    return f'''<section class="row"><h3>{html.escape(name)}<span class="tag">{html.escape(kind)}</span></h3><p class="why">{html.escape(why)}</p>
<div class="quad">{cell("Video %d, %s (%g s)" % (v, frame, (int(frame[1:]) - 1) / 2), real)}{cell("Rebuilt, bloom", fn("bloom")) if v == 4 else cell("Rebuilt, halftone", fn("halftone")) if v == 3 else cell("Rebuilt, ember", fn("ember"))}{cell("Rebuilt, ember", fn("ember")) if v == 4 else cell("Rebuilt, glow", fn("glow")) if v == 3 else cell("Rebuilt, original (paper)", fn("paper"))}{cell("Rebuilt, original (paper)", fn("paper")) if v >= 3 else cell("Rebuilt, glow", fn("glow"))}</div></section>'''


def main():
    import json
    rows = "".join(row(*c) for c in COMPONENTS)
    rows2 = "".join(row(*c, v=2) for c in COMPONENTS2)
    rows3 = "".join(row(*c, v=3) for c in COMPONENTS3)
    rows4 = "".join(row(*c, v=4) for c in COMPONENTS4)
    crop_img = lambda f, alt: fit('<img src="%s" width="640" height="360" alt="%s">' % (crop(f, 0, 0, 640, 360), alt), 640, 360)
    lab_bright, lab_dim = crop_img("f013", "the video bright ground, frame f013"), crop_img("f078", "the video dim ground, frame f078")
    gcrop = lambda f, x, y: fit('<img src="%s" width="640" height="360" alt="the video glow ground, frame %s">' % (crop(f, x, y, 640, 360, 2), f), 640, 360)
    glab_win, glab_claim, glab_lock = gcrop("f009", 640, 0), gcrop("f059", 0, 0), gcrop("f062", 0, 720)
    glab_stage = fit('<div style="position:relative;width:640px;height:360px;overflow:hidden"><div class="ag" id="glab-stage" data-theme="glow" style="position:absolute;left:-640px;top:0;width:1920px;height:1080px"><div class="ag-ground" id="glab-ground"></div></div></div>', 640, 360)
    lab_stage = fit('<div class="ag" id="lab-stage" data-theme="ember" style="width:640px;height:360px"><div class="ag-ground" id="lab-ground"></div></div>', 640, 360)
    stats = "".join(f"<tr><td>{html.escape(k)}</td><td>{html.escape(v)}</td></tr>" for k, v in STATS)
    toks = "".join(f'<tr><td>{n}</td><td class="n"><span class="sw" style="background:{v}"></span>{v}</td><td class="n"><span class="sw ag" data-theme="ember" style="background:{r};position:static"></span>ember: <span class="ag" data-theme="ember" style="display:inline"><span class="tv" style="color:inherit"></span></span>{r}</td></tr>' for n, v, r in TOKENS)
    body = f'''<meta name="claude:viewport-fit-sides" content="cover">
<title>Agent Components</title>
<style>{build.fontface()}{PAGE_CSS}{CSS}{LAB_CSS}</style>
<div class="pg">
<h1>Agent components</h1>
<fieldset class="settings"><legend>Component settings</legend>
 <label><input type="checkbox" id="set-partner" checked> Partner logo is white on dark grounds (ember, and glow's claim and lockup)</label>
 <label><input type="checkbox" id="set-true"> Show every cell at true size, 1:1 (grain, specks and blur are in video pixels, so they are only visible at full size; scroll a cell sideways)</label>
</fieldset>
<div class="tags"><span class="tag">source: the first reference video</span><span class="tag">22 components</span><span class="tag">3 themes: ember, paper, glow</span></div>

<h2 style="margin-top:22px">Ground lab</h2>
<div class="lab">
 <div class="lab-top">
  <div class="tabs"><button class="on" data-mode="bright" type="button">Bright: typing, window</button><button data-mode="dim" type="button">Dim: lockup</button><label class="lift"><input id="lab-lift" type="checkbox"> Brighten both to compare faint lines</label></div>
  <div class="pair">
   <div class="cell"><p class="cap">Video, top-left 640 x 360</p>
    <div id="lab-crop-bright">{lab_bright}</div>
    <div id="lab-crop-dim" hidden>{lab_dim}</div></div>
   <div class="cell"><p class="cap">Shader</p>{lab_stage}</div>
  </div>
 </div>
 <div class="lab-ctl">
  <div id="lab-sliders"></div>
  <div class="tabs"><button id="lab-reset" type="button">Reset to preset</button><button id="lab-copy" type="button">Copy parameters</button></div><pre id="lab-params" aria-live="polite"></pre>
  <p class="lede">The video's ground is a graph-paper grid whose lines are speckled with grain. This is that ground as a small turbulence shader (<code>components/agent/ground.js</code>), with every parameter on a slider so you can match it by eye. The shader has no time input, so a set of parameters is one frozen picture; <b>seed</b> chooses which. Copy the parameters when you like them and they become the preset a film freezes on. The shader is an SVG filter, not WebGL, because the film renderer's Chrome has no GPU.</p>
 </div>
</div>

<h2 style="margin-top:34px">Glow grain lab</h2>
<p class="lede">The glow ground is a plain light-to-dark gradient with red speckle on top. The speckle is a random mask; a fade along the same diagonal runs the red out where you want the gradient to show through. The claim and lockup grounds keep their own dark bases under a faint red speckle.</p>
<div class="lab" id="glab">
 <div class="lab-top">
  <div class="tabs"><button class="on" data-gmode="window" type="button">Window beats</button><button data-gmode="claim" type="button">Claim</button><button data-gmode="lockup" type="button">Lockup</button></div>
  <div class="pair">
   <div class="cell"><p class="cap">Video, same 640 x 360 region</p>
    <div id="glab-crop-window">{glab_win}</div><div id="glab-crop-claim" hidden>{glab_claim}</div><div id="glab-crop-lockup" hidden>{glab_lock}</div></div>
   <div class="cell"><p class="cap">Glow ground</p>{glab_stage}</div>
  </div>
 </div>
 <div class="lab-ctl">
  <div id="glab-sliders"></div>
  <div class="blendrow"><label for="glab-light">Gradient light <input type="color" id="glab-light" value="#ef9a30"></label><label for="glab-dark">Gradient dark <input type="color" id="glab-dark" value="#0a0000"></label><label for="glab-red">Red speckle <input type="color" id="glab-red" value="#bd2417"></label><label for="glab-blend">Blend <select id="glab-blend"><option>normal</option><option>hard-light</option><option>soft-light</option><option>overlay</option><option>multiply</option><option>screen</option></select></label></div>
  <div class="tabs"><button id="glab-reset" type="button">Reset to preset</button><button id="glab-copy" type="button">Copy parameters</button></div><pre id="glab-params" aria-live="polite"></pre>
 </div>
</div>

<p class="lede">What the two agent reference videos draw, rebuilt as shared components and set beside the real frames. Each row is the video's frame, then the rebuild on three themes: ember (the first video's), paper (the original comparison layout's) and glow (the second video's). The components are in <code>components/agent/agent.css</code>, tokens only; nothing in them belongs to a kit.</p>

<h2>Geometry: video against rebuild</h2>
<p class="lede">The video's numbers are read off its frames; the rebuilt column is measured in your browser right now. A box marked <b>set</b> is given the video's size, so it matches by construction. A box marked <b>measured</b> is sized by its own content (text wrapping, the icons beside it), which is the real test; within 3% shows green.</p>
<div class="tblwrap"><table class="tbl"><thead><tr><th>Part</th><th>Basis</th><th>Video (px)</th><th>Rebuilt (px)</th><th>Difference</th></tr></thead><tbody id="geo"></tbody></table></div>

<h2>What the video is</h2>
<div class="tblwrap"><table class="tbl"><tbody>{stats}</tbody></table></div>

<h2>Components</h2>
<p class="lede">Tags: <b>new</b> means the comparison layout has nothing like it; <b>theme</b> means it has the part and the video only restyles it. Fonts are the house's Manrope and Sometype Mono, as everywhere in this repo; the video's own interface face was not identified, so letterforms differ slightly.</p>
{rows}
<h2>From the second video</h2>
<p class="lede">The same app in a light window on a grain gradient (Muse Spark Open, a pricing review). Most of it is components you have already seen, restyled by the <b>glow</b> theme; what is new is drawn once here and shown in all three themes. Columns: the video, ember, the original paper, glow.</p>
{rows2}
<h2>From the third video</h2>
<p class="lede">The same app again (Kimi K3.1 Pro, buying a monitor), on a flat vermilion ground with a halftone. New here: the <b>halftone</b> theme, the pill composer, the timer pill, the order card with confetti, and a generic store page in the browser pane. Columns: the video, then the rebuild in halftone, glow and paper. A full-frame comparison with a difference image is in the Agent video 3 page.</p>
{rows3}
<h2>From the fourth video</h2>
<p class="lede">The first video's dark window and browser pane again (Kimi 3.1 Pro, ordering a sandwich), on the new <b>bloom</b> ground: a blurred black blob, ochre and crimson glows and film grain. New here: the bloom ground, the assistant's question and the user's one-word answer, and a stand-in food-delivery site in the pane. Columns: the video, then the rebuild in bloom, ember and paper.</p>
{rows4}
</div>
<script>{BLOOM_JS}</script><script>{GROUND_JS}</script>
<script>AgGround.mountAll();</script>
{LAB_JS}
{GLAB_JS}
{SETTINGS_JS}
{FIT_JS % json.dumps({k: list(v) for k, v in VIDEO.items()})}
'''
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, "agent-components.artifact.html")
    open(p, "w", encoding="utf-8").write(body)
    open(os.path.join(OUT, "agent-components.page.html"), "w", encoding="utf-8").write("<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'></head><body>" + body + "</body></html>")
    print(p, len(body) // 1024, "KB")


if __name__ == "__main__":
    main()
