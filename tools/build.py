#!/usr/bin/env python3
"""A race config -> the film page, the timeline, the inline blocks.

    python3 tools/build.py <config>.json           # everything under out/
    python3 tools/build.py <config>.json --beats   # and print the beat sheet

Writes, for a config `<slug>`:

    out/<kit>/<slug>.html            the FILM: open it and it plays; ?scrub for a slider over
                               every named beat; ?t=<beat|ms> holds one instant;
                               ?render is what agent-film.mjs and check.mjs drive
    out/<kit>/<slug>.timeline.json   the derived timeline (what an inline block fetches)
    out/<kit>/<slug>.inline.html     a stand-in host page with the format's INLINE BLOCKS
                               at several widths and act/lane selections
    out/<kit>/<slug>.fragment.html   the paste-able fragment: one block with its timeline
                               inlined, for a page that has sheet.css + engine.js
    out/<kit>/sheet.css, out/<kit>/engine.js  the sheet and the engine, copied beside the outputs

Fonts, the sheet, the engine and the derived timeline are all inlined into the
film page, so a file:// URL is enough. Brand marks and attachment thumbnails
that point at files (`"mark": "path.svg"`, `"thumb": "path.png"`) are inlined
too, resolved against the config's directory."""
import base64, json, mimetypes, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))   # tools/
ROOT = os.path.dirname(HERE)                         # the repo: layouts/, kits/, brand/, fonts/, out/
LAYOUTS = os.path.join(ROOT, "layouts")
sys.path.insert(0, HERE)

# A LAYOUT is a folder under layouts/: its engine (engine.js), its sheet (sheet.css), its
# derive.py (config -> timeline), its templates and its gate. A config belongs to the
# layout its folder is named after (configs/<layout>/<name>.json). build.py is shared:
# it loads the layout's derive.py and reads the layout's files, and everything else
# (fonts, brand files, captures, out/) is the repo's.
_layouts = {}


def layout_module(name):
    """the layout's derive.py, loaded once"""
    if name not in _layouts:
        import importlib.util
        p = os.path.join(LAYOUTS, name, "derive.py")
        if not os.path.exists(p):
            raise SystemExit(f"no layout '{name}' (layouts/: {', '.join(sorted(os.listdir(LAYOUTS)))})")
        spec = importlib.util.spec_from_file_location(f"derive_{name}", p)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        _layouts[name] = m
    return _layouts[name]


def layout_of(config_path):
    """configs/<layout>/x.json -> <layout>; a config elsewhere is the comparison's"""
    d = os.path.basename(os.path.dirname(os.path.abspath(config_path)))
    return d if os.path.isdir(os.path.join(LAYOUTS, d)) else "comparison"


LAYOUT = "comparison"


class _NoLayout:
    class Refusal(Exception):
        pass


derive = _NoLayout   # this repository ships the film kit only: no comparison layout to load


def use_layout(name):
    global LAYOUT, derive
    LAYOUT, derive = name, layout_module(name)


def kit_root(config_path):
    """kits/<kit>/configs/<layout>/x.json -> kits/<kit>: the folder that owns the config's
    captures/, brand/ and examples/ (a kit is one model partner, Cerebras x {model})"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(config_path))))


def kit_of(config_path):
    return os.path.basename(kit_root(config_path))


def out_dir_of(config_path):
    """built pages and films go in out/<kit>/, so two kits never overwrite each other"""
    return os.path.join(ROOT, "out", kit_of(config_path))


def layout_dir():
    return os.path.join(LAYOUTS, LAYOUT)

# THE FACES ARE CEREBRAS.AI'S, identified from the files' own name tables
# (fonts/FONTS.md): Manrope (variable, 200-800) for everything sans and
# Sometype Mono (variable, 400-700) for everything mono. Both inlined, so a
# built page and a render draw the same faces on any machine. DEMOKIT_FONTS
# points at another folder with the same file names.
FONT_DIRS = [os.environ.get("DEMOKIT_FONTS", ""), os.path.join(ROOT, "fonts", "cerebras"), os.path.join(ROOT, "fonts")]
FONTS = [("Manrope", "200 800", "Manrope[wght].woff2", "woff2"),
         ("Sometype Mono", "400 700", "SometypeMono[wght].woff2", "woff2")]

# THE FALLBACK FACE. Manrope and Sometype Mono are Latin faces; a config in
# another script (Arabic, Chinese, Japanese, Korean) needs glyphs they do not
# have. A page carries them as one more family, 'DemoKit Fallback', named after
# the site's faces in sheet.css's stacks so Latin keeps coming from Manrope:
# each script's face is SUBSET at build to the characters the page actually
# uses (pyftsubset, from fonttools) and inlined like the others, so a render
# in the cloud draws the same glyphs as one here. The source file for a
# script is the first that exists: fonts/fallback/<script>.ttf|otf (drop a
# chosen face there), else what the machine has. Without pyftsubset the page
# names the family and the viewer's own fonts fill it, with a warning.
SCRIPTS = {
    "arabic": {"ranges": [(0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF)],
               "sources": ["/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                           "/System/Library/Fonts/Supplemental/Arial Unicode.ttf", "C:/Windows/Fonts/segoeui.ttf"]},
    "cjk": {"ranges": [(0x2E80, 0x9FFF), (0x3000, 0x30FF), (0xAC00, 0xD7AF), (0xF900, 0xFAFF), (0xFF00, 0xFFEF)],
            "sources": ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
                        "/System/Library/Fonts/PingFang.ttc", "C:/Windows/Fonts/msyh.ttc"]},
}


def fallback_fontface(text):
    """@font-face rules for every script in `text` that the site's faces lack"""
    import hashlib, shutil, subprocess, sys, tempfile
    css = []
    for script, spec in SCRIPTS.items():
        chars = sorted({c for c in text if any(lo <= ord(c) <= hi for lo, hi in spec["ranges"])})
        if not chars:
            continue
        urange = ", ".join(f"U+{lo:04X}-{hi:04X}" for lo, hi in spec["ranges"])
        src = None
        for cand in [os.path.join(ROOT, "fonts", "fallback", script + ext) for ext in (".ttf", ".otf", ".ttc")] + spec["sources"]:
            if os.path.exists(cand):
                src = cand; break
        tool = shutil.which("pyftsubset")
        if not src or not tool:
            print(f"WARNING: {script} text on the page but {'no face for it (fonts/fallback/' + script + '.ttf, or one the machine has)' if not src else 'no pyftsubset (pip install fonttools brotli)'}: "
                  f"the viewer's own fonts will fill 'DemoKit Fallback'", file=sys.stderr)
            continue
        key = hashlib.sha1((src + "".join(chars)).encode("utf-8")).hexdigest()[:16]
        cache = os.path.join(ROOT, "out", "_fonts"); os.makedirs(cache, exist_ok=True)
        woff = os.path.join(cache, f"{script}-{key}.woff2")
        if not os.path.exists(woff):
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
                tf.write("".join(chars)); tf.flush(); textfile = tf.name
            args = [tool, src, f"--text-file={textfile}", "--flavor=woff2", f"--output-file={woff}", "--no-hinting", "--desubroutinize"]
            if src.endswith(".ttc"):
                args.append("--font-number=0")
            r = subprocess.run(args, capture_output=True, text=True)
            os.unlink(textfile)
            if r.returncode != 0 or not os.path.exists(woff):
                print(f"WARNING: pyftsubset failed on {src}: {r.stderr.strip()[-200:]}", file=sys.stderr)
                continue
        b = base64.b64encode(open(woff, "rb").read()).decode()
        css.append(f"@font-face{{font-family:'DemoKit Fallback';font-weight:100 900;font-style:normal;font-display:block;unicode-range:{urange};"
                   f"src:url(data:font/woff2;base64,{b}) format('woff2');}}")
    return "\n".join(css)


def fontface(text=""):
    """the site's two faces, plus a fallback face for any other script in `text`"""
    css = []
    for family, weight, fname, fmt in FONTS:
        for d in FONT_DIRS:
            p = os.path.join(d, fname) if d else None
            if p and os.path.exists(p):
                b = base64.b64encode(open(p, "rb").read()).decode()
                mime = "font/woff2" if fmt == "woff2" else "font/otf"
                fmt_css = "woff2-variations" if " " in str(weight) and fmt == "woff2" else fmt
                css.append(f"@font-face{{font-family:'{family}';font-weight:{weight};font-style:normal;font-display:block;"
                           f"src:url(data:{mime};base64,{b}) format('{fmt_css}');}}")
                break
    fb = fallback_fontface(text) if text else ""
    return "\n".join(css) + ("\n" + fb if fb else "")


def inline_file(cfg_dir, ref):
    # `@brand/<path>` is the house's (Cerebras) shared marks, brand/ at the repo root;
    # anything else is relative to the config's own folder (the kit's brand/)
    if ref.startswith("@brand/"):
        p = os.path.join(ROOT, "brand", ref[len("@brand/"):])
    else:
        p = ref if os.path.isabs(ref) else os.path.join(cfg_dir, ref)
    if not os.path.exists(p):
        raise derive.Refusal(f"file not found: {ref} (looked at {p})")
    if p.lower().endswith(".svg"):
        svg = open(p, encoding="utf-8").read()
        svg = svg[svg.index("<svg"):]                      # no XML prolog, no DOCTYPE
        head_end = svg.index(">")
        head = re.sub(r'\s(width|height)="[^"]*"', "", svg[:head_end])   # sized by the box it sits in
        # an Illustrator export declares the ART'S bounds as its mask rect; when
        # that is smaller than the viewBox the art sits small and off-centre in
        # any box, so the viewBox is tightened to it (the Cerebras icon's art is
        # 31 x 40 inside a 47 x 47 box; the full logo's mask is the whole box)
        # ... unless the file carries an explicit FRAME: an unfilled rect
        # (fill="none") is how a designer says "this is the box the art is
        # centred in" - the icon re-exported 2026-09-12 does exactly that, and
        # tightening past it would undo the centring it was made for
        framed = re.search(r'<(rect|circle|ellipse)[^>]*fill="none"', svg) is not None
        m = re.search(r'<mask[^>]*maskUnits="userSpaceOnUse"[^>]*\sx="([\d.]+)"[^>]*\sy="([\d.]+)"[^>]*\swidth="([\d.]+)"[^>]*\sheight="([\d.]+)"', svg)
        vb = re.search(r'viewBox="([\d.\s-]+)"', head)
        if m and vb and not framed:
            x, y, w, h = (float(v) for v in m.groups())
            vx, vy, vw, vh = (float(v) for v in vb.group(1).split())
            if w < vw * .95 or h < vh * .95:
                head = head.replace(vb.group(0), f'viewBox="{x:g} {y:g} {w:g} {h:g}"')
        svg = head + svg[head_end:]
        # EVERY id IS NAMESPACED BY FILE. Illustrator gives every export the same
        # ids (the three Cerebras files all carry mask-for-h-1211), and a page
        # inlines several files many times over; url(#id) resolves to the FIRST
        # element with that id in the whole document, so a logo drawn after an
        # icon took the icon's mask and lost its wordmark. Found 2026-09-13 on
        # the gallery. The suffix is the file's name, so copies of one file
        # still share their ids (identical, harmless) and different files never do.
        tag = re.sub(r"[^A-Za-z0-9]+", "-", os.path.splitext(os.path.basename(p))[0])
        ids = set(re.findall(r'\sid="([^"]+)"', svg))
        for i in sorted(ids, key=len, reverse=True):
            svg = svg.replace(f'id="{i}"', f'id="{i}-{tag}"')
            svg = re.sub(r'url\(#' + re.escape(i) + r'\)', f'url(#{i}-{tag})', svg)
            svg = re.sub(r'(xlink:href|href)="#' + re.escape(i) + '"', f'\\1="#{i}-{tag}"', svg)
        return svg
    mime = mimetypes.guess_type(p)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(open(p, 'rb').read()).decode()}"


def read(name):
    """a file of the current layout's folder"""
    return open(os.path.join(layout_dir(), name), encoding="utf-8").read()


def engine_js():
    """the engine: engine.js, as is"""
    return read("engine.js")


def engine_min():
    """the engine minified for a public embed: no comments, names mangled.
    terser (a dev dependency) does it; without it the public build refuses
    rather than shipping the commented source under a name that promises
    otherwise."""
    import shutil, subprocess
    npx = shutil.which("npx")
    src = read("engine.js")
    flag = "const PUBLIC = false;"
    if src.count(flag) != 1:
        raise derive.Refusal("engine.js must declare `const PUBLIC = false;` exactly once: the public build flips it and terser drops what it guards")
    src = src.replace(flag, "const PUBLIC = true;")   # the scrubber and the render branch are `!PUBLIC &&` guarded: dead code, dropped
    r = subprocess.run([npx or "npx", "--no-install", "terser", "--compress", "--mangle", "--comments", "false"],
                       input=src, capture_output=True, text=True, cwd=ROOT) if npx else None
    if r is None or r.returncode != 0 or not r.stdout.strip():
        raise derive.Refusal("the public build needs terser: npm install (it is a devDependency)" + (("; " + r.stderr.strip()[-160:]) if r and r.stderr else ""))
    return r.stdout


def sheet_public():
    """THE SHEET A VIEWER GETS: sheet.css with its comments stripped. The
    comments are the design's account of itself (what was sampled, what was
    ruled and when, which gate holds it) and stay in the private build with
    the engine's; the rules are what a page needs. Ruled 2026-09-14 after a
    blind read of a published page quoted the rulings back."""
    import re
    css = re.sub(r"/\*.*?\*/", "", read("sheet.css"), flags=re.S)
    css = re.sub(r"\.dk-scrub[^{}]*\{[^{}]*\}", "", css)   # the scrubber's rules go with the scrubber (whole rules: one spans two lines)
    return "\n".join(l.rstrip() for l in css.splitlines() if l.strip()) + "\n"


def public_timeline(tl):
    """THE TIMELINE A VIEWER GETS. An inline block ships its timeline in the
    page, readable by anyone who opens the source. The engine needs the beats,
    the clocks, the words and the captured text (all of which are on screen
    anyway); it does not need the resolved config (its `why`, the claim's
    `source`), derive's warnings (the measured ratio against the claim in
    words), the measured ratio itself, or the config's name. Those are the
    system's own account of itself and stay in the private build."""
    import copy
    t = copy.deepcopy(tl)
    for k in ("config", "warnings", "name", "slug"):
        t.pop(k, None)
    t["claim"].pop("measured", None)
    # what the engine never reads (2026-09-14, after a blind read of a page
    # rebuilt derive's arithmetic from it): the pace knobs derive consumed
    # (the engine reads three), the lane-clock copies of the section times,
    # the lanes' brand names, and the brand files' paths once their SVGs are
    # inlined. check-public.mjs reads this back off the mounted block.
    t["timing"] = {k: v for k, v in t["timing"].items() if k in ENGINE_TIMING}
    for lane in t["race"]["lanes"].values():
        lane.pop("brandName", None)
        for s in lane["sections"]:
            s.pop("thinkLane", None); s.pop("showLane", None)
    for b in t["brands"].values():
        if b.get("markSvg"): b.pop("mark", None)
        if b.get("logoSvg"): b.pop("logo", None)
        if b.get("wordmarkSvg"): b.pop("wordmark", None)
    return t


ENGINE_TIMING = ("cross", "pointer", "enter")   # the only `timing` keys engine.js reads; check-api.py holds this against the source


def all_configs():
    """every config of every kit: kits/<kit>/configs/<layout>/<name>.json"""
    kits = os.path.join(ROOT, "kits")
    out = []
    for kit in sorted(os.listdir(kits)):
        cdir = os.path.join(kits, kit, "configs")
        if kit.startswith("_") or not os.path.isdir(cdir):
            continue
        for lay in sorted(os.listdir(cdir)):
            ld = os.path.join(cdir, lay)
            out += [os.path.join(ld, f) for f in sorted(os.listdir(ld)) if os.path.isdir(ld) and f.endswith(".json") and not f.startswith("_")]
    return out


def config_path(arg):
    """a path, `<kit>/<name>`, or a bare name looked up in every kit"""
    if os.path.exists(arg):
        return arg
    name = arg if arg.endswith(".json") else arg + ".json"
    have = all_configs()
    hits = []
    for cand in have:
        rel = os.path.relpath(cand, os.path.join(ROOT, "kits")).replace(os.sep, "/")
        short = rel.replace("/configs/", "/", 1)                      # <kit>/<layout>/<name>.json
        if "/" in arg:
            if short.endswith(name) or short.replace("/", "/", 1).split("/", 1)[0] + "/" + os.path.basename(cand) == name:
                hits.append(cand)
        elif os.path.basename(cand) == name:
            hits.append(cand)
    if len(hits) > 1:
        raise derive.Refusal(f"'{arg}' is in more than one kit; say which: {', '.join(os.path.relpath(c, os.path.join(ROOT, 'kits')) for c in hits)}")
    if hits:
        return hits[0]
    raise derive.Refusal(f"no config at {arg} (kits: {', '.join(os.path.relpath(c, os.path.join(ROOT, 'kits')) for c in have)})")


def timeline(config_arg):
    path = config_path(config_arg)
    use_layout(layout_of(path))
    cfg = derive.load(path)
    tl = derive.derive(cfg)
    for bid, b in tl["brands"].items():
        if str(b.get("mark", "")).lower().endswith(".svg"):
            b["markSvg"] = inline_file(cfg["_dir"], b["mark"])
        if b.get("wordmark"):
            b["wordmarkSvg"] = inline_file(cfg["_dir"], b["wordmark"])
        if b.get("logo"):
            b["logoSvg"] = inline_file(cfg["_dir"], b["logo"])
    at = tl["compose"].get("attachment")
    if at and at.get("thumb"):
        at["thumb"] = inline_file(cfg["_dir"], at["thumb"])
    return tl


def build(config_arg, out_dir=None):
    tl = timeline(config_arg)
    out_dir = out_dir or out_dir_of(globals()["config_path"](config_arg))
    os.makedirs(out_dir, exist_ok=True)
    slug = tl["slug"]
    tl_json = json.dumps(tl).replace("</", "<\\/")
    fonts, css, js = fontface(json.dumps(tl, ensure_ascii=False)), read("sheet.css"), engine_js()
    fill = lambda tpl: (tpl.replace("__TITLE__", tl["name"]).replace("__SLUG__", slug)
                        .replace("__FONTS__", fonts).replace("__DEMOKIT_CSS__", css)
                        .replace("__DEMOKIT_JS__", js).replace("__TIMELINE__", tl_json)
                        .replace("__TIMELINE_SCRIPT__", '<script type="application/json">' + tl_json + '</script>'))
    outputs = {
        slug + ".html": fill(read("template.html")),
        slug + ".inline.html": fill(read("inline-template.html")),
        slug + ".fragment.html": ('<div data-demo data-acts="compose,race,claim,lockup">'
                                  '<script type="application/json">' + tl_json + '</script></div>\n'),
        slug + ".timeline.json": json.dumps(tl, indent=1),
    }
    # THE PUBLIC BUILD: what leaves this repository for a page other people
    # read. The same block, on the minified engine, with the pruned timeline
    # (public_timeline). `.public.html` is the stand-in host page for it, and
    # the proof that it paints the same frames is check.sh's public step.
    pub = json.dumps(public_timeline(tl), separators=(",", ":")).replace("</", "<\\/")
    try:
        js_min = engine_min()
    except derive.Refusal as e:
        print(f"WARNING: no public build: {e}", file=sys.stderr)
        js_min = None
    if js_min:
        fill_pub = lambda tpl: (tpl.replace("__TITLE__", tl["name"]).replace("__SLUG__", slug)
                                .replace("__FONTS__", fonts).replace("__DEMOKIT_CSS__", sheet_public())
                                .replace("__DEMOKIT_JS__", js_min).replace("__TIMELINE__", pub)
                                .replace("__TIMELINE_SCRIPT__", '<script type="application/json">' + pub + '</script>'))
        outputs[slug + ".public.fragment.html"] = ('<div data-demo data-acts="compose,race,claim,lockup">'
                                                   '<script type="application/json">' + pub + '</script></div>\n')
        outputs[slug + ".public.html"] = fill_pub(read("inline-template.html"))
        outputs[slug + ".public.timeline.json"] = pub
        open(os.path.join(out_dir, "engine.min.js"), "w", encoding="utf-8").write(js_min)
    for name, text in outputs.items():
        open(os.path.join(out_dir, name), "w", encoding="utf-8").write(text)
    shutil.copyfile(os.path.join(layout_dir(), "sheet.css"), os.path.join(out_dir, "sheet.css"))
    open(os.path.join(out_dir, "engine.js"), "w", encoding="utf-8").write(js)
    return os.path.join(out_dir, slug + ".html"), tl


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__); sys.exit(2)
    try:
        html, tl = build(args[0])
    except derive.Refusal as e:
        print(f"refused: {e}", file=sys.stderr); sys.exit(1)
    if "--beats" in sys.argv:
        print(derive.beat_sheet(tl))
    for w in tl["warnings"]:
        print(f"WARNING: {w}", file=sys.stderr)
    print(html)
