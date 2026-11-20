#!/usr/bin/env python3
"""AGENT FILM: a storyboard (JSON) -> one deterministic HTML page the renderer can seek -> an MP4.

    python3 artifact/agent_film.py templates/agent-film/storyboard.json      build out/agent-film/<slug>/film.html
    node tools/agent-film.mjs out/agent-film/<slug>/film.html [--fps 30] [--out x.mp4] [--png-at 4500]   photograph it

The film is built from the SAME shared components and themes as the review pages (artifact/agent_components.py, agent_pages.py, components/agent/agent.css), with the
words of the storyboard in them, and it holds no words of its own. Scenes (any order, any number): typing, welcome, turn, answer, popin, claim, lockup. Read
templates/agent-film/README.md for the storyboard's keys; every unknown key is refused, as derive.py refuses them for the comparison layout.

`popin` is the pop-your-video-in scene: the user's own 16:9 clip, with rounded corners, REPLACES the white window (its frames are extracted with ffmpeg and swapped in by time),
for a user who has no recording that the components could recreate. The house styling is then the text states around it: typing, claim, lockup.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "tools"))
import agent_components as A  # noqa: E402
import agent_pages as Pg  # noqa: E402
import build  # noqa: E402

THEMES = ("ember", "paper", "glow", "halftone", "bloom", "tile")   # THE list: every tool and page that needs the themes imports it (a new theme is added here, in agent.css, and in ground.js if its ground is a canvas)
SLOW_GROUND_THEMES = ("glow", "bloom", "tile")   # a canvas ground that renders slowly and makes big windows: the cloud uses 16 windows
SCENES = tuple(("intro", "typing", "welcome", "turn", "answer", "thread", "versus", "popin", "ask", "second-turn", "integration", "browse", "ground", "claim", "lockup"))
KEYS = {"slug", "theme", "model", "prompt", "partner_logo", "fade_ms", "fps", "tool", "meter", "answer", "claim", "popin", "scenes", "why", "attachment", "timer", "words"}   # attachment and timer are OPTIONAL: absent, nothing is drawn for them
SCENE_KEYS = {"scene", "ms", "type_ms", "prompt", "tool", "meter", "answer", "claim", "thread", "tps", "versus", "clip_from", "variant", "cut", "ask", "second", "integration", "browse", "intro"}   # the content keys override the film-wide ones for THIS scene
W, H = 1920, 1080
CLOUD_POPIN_FPS = 12


class Refusal(SystemExit):
    pass


def up_to(model):
    """the stated "up to" tokens a second for this model, or None for a model with none stated"""
    m = str(model).lower()
    return next((v for k, v in MODEL_UP_TO.items() if k in m), None)


def refuse(msg):
    raise Refusal("storyboard refused: " + msg)



# ── THE STATES: what a film can be made of, what may follow what, and how each change is drawn ───────────────────────────────────────────────────────────
# Predictable by construction: load() refuses any storyboard whose first scene, or any scene-to-scene change, is not in these tables, and says what is allowed instead.
# `next` is what may follow (a state may follow itself: a thread can run on in a second scene); `start` whether a film may begin with it. How a change is drawn is not free either: MORPH_FROM below.
STATES = {
    "typing":  {"start": True,  "next": ("welcome", "turn", "answer", "thread", "versus", "popin"),         "what": "the prompt types into the hero composer on the ground"},
    "welcome": {"start": True,  "next": ("turn", "answer", "thread", "versus", "browse", "ask", "claim", "lockup"),          "what": "the window at rest: the mark, the question, the composer holding the prompt"},
    "turn":    {"start": False, "next": ("answer", "thread", "versus", "ask", "browse", "second-turn", "integration", "ground", "claim", "lockup"),                  "what": "the user's bubble, 'Preparing this turn' (the ONE loading indicator), the tool line, the meter"},
    "answer":  {"start": False, "next": ("turn", "thread", "versus", "popin", "ask", "browse", "second-turn", "integration", "ground", "claim", "lockup"),           "what": "'Worked for N seconds', the answer card (streamed word by word if answer.stream_ms is set), the footer, the finished composer"},
    "thread":  {"start": False, "next": ("thread", "turn", "answer", "versus", "popin", "ask", "browse", "second-turn", "integration", "ground", "claim", "lockup"), "what": "a conversation between the user and one or more agents, message after message, each streaming in, scrolling up as it grows; tool lines between"},
    "popin":   {"start": True,  "next": ("thread", "turn", "answer", "versus", "ask", "browse", "second-turn", "integration", "ground", "claim", "lockup"),          "what": "the user's own 16:9 clip, rounded, REPLACES the white window (scene.clip_from starts it part-way in)"},
    "versus":  {"start": False, "next": ("versus", "thread", "turn", "answer", "popin", "ask", "browse", "second-turn", "integration", "ground", "claim", "lockup"), "what": "side by side, the same conversation on a GPU lane and on the Cerebras lane: each streams at its own tokens a second, with a live token count and clock; Cerebras is never below 1,000"},
    "ask":     {"start": False, "next": ("turn", "thread", "versus", "answer", "ground", "claim", "lockup"), "what": "the assistant asks the user a question (a card with answer options) and the turn WAITS; the user's one-word reply arrives, 'Preparing this turn' ticks (reference video 4)"},
    "second-turn": {"start": False, "next": ("answer", "thread", "versus", "turn", "integration", "ground", "claim", "lockup"), "what": "the first exchange stays, a second prompt is typed into the docked composer, the pointer presses send and the conversation scrolls up under a new bubble (reference video 2)"},
    "integration": {"start": False, "next": ("ground", "claim", "lockup"), "what": "the window DEFOCUSES (blur and dim) and a white card builds in over it: a repo or ticket header, a title, a badge, chips and a body that streams (reference video 2's PR card)"},
    "browse":  {"start": False, "next": ("turn", "thread", "versus", "answer", "ask", "ground", "claim", "lockup"), "what": "the chat narrows to the left and the agent's browser pane opens at the right (tabs, address bar, a page that changes and scrolls, an optional modal and pointer click); the chat holds the tool card with a live thumbnail (reference videos 1, 3, 4). The pages are generic stand-ins, never a real site"},
    "intro":   {"start": True,  "next": ("typing", "welcome", "turn", "answer", "thread", "versus", "popin", "browse", "ask", "ground", "claim", "lockup"), "what": "an INTRODUCTION slide: a title and a description (and an optional logo), nothing else, built up progressively on the theme's ground; the opener for a film that is not a rebuild, used instead of the typed prompt"},
    "ground":  {"start": True,  "next": ("typing", "popin", "claim", "lockup"), "what": "the ground alone (the theme's halftone, bloom or tile), for a pause or a title card: the blank beat of the reference videos"},
    "claim":   {"start": True,  "next": ("lockup",),                                            "what": "the model's name, the claim's number dialling up, the footnote"},
    "lockup":  {"start": True,  "next": (),                                                     "what": "the house logo, a hairline, the partner's logo: the end"},
}
# A scene is entered by MORPH only straight after `typing` (the composer BECOMES the next scene's white base, film.js); every other change is a crossfade of `fade_ms`.
MORPH_FROM = ("typing",)
# States the reference videos show that are NOT built. Naming one in a storyboard is refused with this reason, so a future state is added HERE first and in scene_html second.
FUTURE_STATES = {}   # every state the reference videos show is built now (ask, browse, second-turn, integration and the timer pill as an option); a state seen in a NEW reference video goes here first, with its reason, and is refused until it is built

DEFAULTS = {
    "theme": "halftone", "fade_ms": 450, "fps": 30,
    "tool": {"name": "Using Browser", "label": "Working"},
    "meter": {"seconds": 4, "tokens": 856, "rate": "1,000 toks/s", "ttft": "31 ms"},
    "answer": {"lead": "Here is what I found.", "bullets": [], "footer_seconds": 4, "footer_tokens": "1.3k", "stream_ms": 0, "confetti": False},
    "tps": 1000,
    "claim": {"number": 1000, "unit": "tokens per second", "footnote": "*Demo shown with mock data."},
}


def _up(ms, step=500):
    return int(-(-ms // step) * step)


def derive_ms(cfg, sc):
    """a scene's least length, worked out from its content: what the scene needs to build up and be read. Used when `ms` is left out; `ms` may still be given to hold longer"""
    k = sc["scene"]
    fixed = {"welcome": 2500, "turn": 3000, "answer": 6500, "claim": 3500, "lockup": 3000, "ground": 1200}
    if k in fixed:
        return fixed[k]
    if k == "intro":
        return _up(intro_times(sc["intro"])["end"] + INTRO_HOLD_MS)
    if k == "typing":
        return _up(TYPE_START_MS + max(600, len(cfg.get("prompt", "")) * 28) + TYPE_GAP_MS + POINTER_MS + CLICK_LEAD_MS)
    if k == "popin":
        v = (cfg.get("popin") or {}).get("video")
        if not v or not os.path.exists(v):
            refuse('a popin scene needs "popin": {"video": "<path to your video>"} that exists (its length sets the scene)')
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", v], capture_output=True, text=True)
        return _up(max(1000, min(60000, float(r.stdout.strip()) * 1000 / float((cfg.get("popin") or {}).get("speed", 1)) - float(sc.get("clip_from", 0)))))
    if k == "thread":
        return _up(thread_plan({"tps": cfg.get("tps", DEFAULTS["tps"])}, sc)[1] + 3500)
    if k == "versus":
        v = {**VERSUS_DEFAULTS, **(sc.get("versus") or {})}
        return _up(versus_times({"versus": v, "thread": sc["thread"]})["g_film_end"] + DONE_HOLD_MS + 200)
    raise ValueError("no rule")


# ── THE SHAPE OF A STORYBOARD: every key's type, checked BEFORE anything reads it, so a wrong type is a sentence that says what to fix, never a crash ─────────────────────────────────
import math  # noqa: E402

NUM, STR, BOOL = "number", "string", "true or false"


WORDS_HELP = {"up_to": "Up to", "done": "DONE", "sec": "sec", "tokens": "tokens", "tokens_per_s": "tokens/s", "ready": "READY", "analyzing": "ANALYZING", "thinking": "Thinking", "final_answer": "FINAL ANSWER", "follow_up": "Ask a follow-up",
              "placeholder": "Message Cerebras", "welcome_q": "What would you like to do?", "preparing": "Preparing this turn...", "worked_for": "Worked for {n} seconds", "done_in": "Done in {s} seconds · {t} output tokens", "assistant": "Assistant", "just_now": "just now", "ttft": "TTFT"}


def localize(html, words):
    """the few fixed words the film draws, in the user's language: only the words given are replaced (defaults in WORDS_HELP), each in its own markup so a user's text is never touched; numbers stay 1,000 style and the Cerebras name and marks are the brand's"""
    import re as _re
    w = {k: esc(v) for k, v in (words or {}).items()}
    R = []
    if "done" in w: R.append((r">DONE</div>", ">%s</div>" % w["done"]))
    if "sec" in w: R.append((r"(\d+\.\d\d) sec</span>", lambda m: "%s %s</span>" % (m.group(1), w["sec"])))
    if "tokens" in w: R.append((r"</b> tokens</span>", "</b> %s</span>" % w["tokens"]))
    if "tokens_per_s" in w: R.append((r">tokens/s</span>", ">%s</span>" % w["tokens_per_s"]))
    if "ready" in w: R.append((r'data-b="READY"', 'data-b="%s"' % w["ready"]))
    if "analyzing" in w: R.append((r'data-a="ANALYZING"([^>]*)>ANALYZING</span>', lambda m: 'data-a="%s"%s>%s</span>' % (w["analyzing"], m.group(1), w["analyzing"])))
    if "thinking" in w: R.append((r"<span>Thinking</span>", "<span>%s</span>" % w["thinking"]))
    if "final_answer" in w: R.append((r">FINAL ANSWER</span>", ">%s</span>" % w["final_answer"]))
    if "follow_up" in w: R.append((r">Ask a follow-up</div>", ">%s</div>" % w["follow_up"]))
    if "placeholder" in w: R.append((r'ag-ph">Message Cerebras</span>', 'ag-ph">%s</span>' % w["placeholder"]))
    if "welcome_q" in w: R.append((r"What would you like to do\?</div>", "%s</div>" % w["welcome_q"]))
    if "preparing" in w: R.append((r"Preparing this turn\.\.\.( <span data-elapsed)", lambda m: "%s%s" % (w["preparing"], m.group(1))))
    if "worked_for" in w: R.append((r"Worked for (<span[^>]*>[\d.,]+</span>|\d+) seconds", lambda m: w["worked_for"].replace("{n}", m.group(1))))
    if "done_in" in w: R.append((r"Done in (<span[^>]*>[^<]*</span>) seconds &nbsp;·&nbsp; (<span[^>]*>[^<]*</span>) output tokens", lambda m: w["done_in"].replace("{s}", m.group(1)).replace("{t}", m.group(2))))
    if "assistant" in w: R.append((r'>Assistant(<span class="ag-chip")', lambda m: ">%s%s" % (w["assistant"], m.group(1))))
    if "just_now" in w: R.append((r"<span>just now</span>", "<span>%s</span>" % w["just_now"]))
    if "ttft" in w: R.append((r" · TTFT ", " · %s " % w["ttft"]))
    if "up_to" in w: R.append((r'Up to (<span class="ag-n")', lambda m: "%s %s" % (w["up_to"], m.group(1))))
    for pat, rp in R:
        html = _re.sub(pat, rp, html)
    return html


def _list(spec, maxn=400):
    return ("list", spec, maxn)


ANSWER_SHAPE = {"lead": STR, "bullets": _list("bullet", 12), "footer_seconds": NUM, "footer_tokens": "strnum", "stream_ms": NUM, "confetti": BOOL}
MESSAGE_SHAPE = {"who": STR, "text": STR, "kind": STR, "title": STR, "verdict": BOOL}
SHAPES = {
    "slug": STR, "theme": STR, "model": STR, "prompt": STR, "partner_logo": STR, "why": STR, "fade_ms": NUM, "fps": NUM, "timer": BOOL,
    "tool": {"name": STR, "label": STR}, "meter": {"seconds": NUM, "tokens": NUM, "rate": STR, "ttft": STR}, "answer": ANSWER_SHAPE,
    "claim": {"number": NUM, "unit": STR, "footnote": STR}, "popin": {"video": STR, "speed": NUM, "frames": NUM, "fit": STR, "base": NUM},
    "attachment": {"title": STR, "meta": STR, "thumb": STR}, "tps": NUM,
    "words": {k: STR for k in ("up_to", "done", "sec", "tokens", "tokens_per_s", "ready", "analyzing", "thinking", "final_answer", "follow_up", "placeholder", "welcome_q", "preparing", "worked_for", "done_in", "assistant", "just_now", "ttft")},
}
SCENE_SHAPES = {
    "scene": STR, "ms": NUM, "type_ms": NUM, "prompt": STR, "tool": SHAPES["tool"], "meter": SHAPES["meter"], "answer": ANSWER_SHAPE, "claim": SHAPES["claim"], "tps": NUM, "clip_from": NUM, "variant": STR, "cut": BOOL,
    "thread": _list(MESSAGE_SHAPE, 300),
    "versus": {"gpu_tps": NUM, "gpu_tps_range": _list(NUM, 2), "cerebras_tps": NUM, "gpu_label": STR, "cerebras_label": STR, "note": STR, "view": STR, "fast_forward": NUM},
    "ask": {"question": STR, "options": _list(STR, 8), "reply": STR}, "second": {"prompt": STR, "type_ms": NUM},
    "integration": {"tag": STR, "title": STR, "badge": STR, "chips": _list(STR, 8), "body": _list(STR, 12)},
    "browse": {"pages": _list({"url": STR, "title": STR, "heading": STR, "lines": _list(STR, 12), "button": STR, "scroll": NUM, "modal": {"title": STR, "buttons": _list(STR, 4)}, "pointer": BOOL, "ms": NUM}, 12)},
    "intro": {"title": STR, "description": STR, "logo": STR, "lockup": BOOL},
}
# how long a text may be: a slide and a lane are not a page; past these a text is unreadable or clipped, so it is refused with the number
LIMITS = {"slug": 60, "model": 60, "prompt": 400, "title": 80, "description": 320, "who": 40, "text": 1200, "lead": 200, "question": 300, "reply": 120, "heading": 100, "unit": 40, "footnote": 160, "note": 300, "url": 120, "name": 80, "meta": 80, "label": 40, "button": 40, "badge": 30}


RANGES = {"fps": (1, 60), "fade_ms": (0, 3000), "ms": (600, 600000), "speed": (0.1, 8), "tps": (1, 100000), "type_ms": (0, 60000), "clip_from": (0, 3600000), "scroll": (0, 5000),
          "gpu_tps": (0.1, 100000), "cerebras_tps": (1, 100000), "fast_forward": (0, 100), "number": (0, 10 ** 7), "stream_ms": (0, 60000), "footer_seconds": (0, 100000), "seconds": (0, 100000), "tokens": (0, 10 ** 9), "frames": (0, 10 ** 6)}


def _shape(path, v, spec):
    where = path or "the storyboard"
    if spec == STR:
        if not isinstance(v, str):
            refuse("%s must be a string (text in quotes), not %s" % (where, type(v).__name__))
        k = path.rsplit(".", 1)[-1].split("[")[0]
        if k in LIMITS and len(v) > LIMITS[k]:
            refuse("%s is %d characters; at most %d (a slide and a lane are not a page: shorten it)" % (where, len(v), LIMITS[k]))
        if len(v) > 5000:
            refuse("%s is %d characters, far too long for a film" % (where, len(v)))
    elif spec == NUM:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > 10 ** 9:
            refuse("%s must be a number (not text, true/false, or an absurd value), not %r" % (where, v if not isinstance(v, (list, dict)) else type(v).__name__))
        k = path.rsplit(".", 1)[-1].split("[")[0]
        if k in RANGES and not RANGES[k][0] <= v <= RANGES[k][1]:
            refuse("%s is %r; it must be between %s and %s" % (where, v, RANGES[k][0], RANGES[k][1]))
    elif spec == BOOL:
        if not isinstance(v, bool):
            refuse("%s must be true or false, not %r" % (where, v if not isinstance(v, (list, dict)) else type(v).__name__))
    elif spec == "strnum":
        if isinstance(v, bool) or not isinstance(v, (str, int, float)):
            refuse("%s must be text or a number" % where)
    elif spec == "bullet":
        ok = isinstance(v, str) or (isinstance(v, list) and len(v) == 2 and all(isinstance(x, str) for x in v))
        if not ok:
            refuse('%s must be a string, or ["Bold run-in:", "the rest"]' % where)
        if len(" ".join(v) if isinstance(v, list) else v) > 400:
            refuse("%s is too long for a bullet (at most 400 characters)" % where)
    elif isinstance(spec, tuple) and spec[0] == "list":
        if not isinstance(v, list):
            refuse("%s must be a list [ ... ], not %s" % (where, type(v).__name__))
        if len(v) > spec[2]:
            refuse("%s has %d items; at most %d" % (where, len(v), spec[2]))
        for j, x in enumerate(v):
            _shape("%s[%d]" % (path, j), x, spec[1])
    elif isinstance(spec, dict):
        if not isinstance(v, dict):
            refuse("%s must be an object { ... }, not %s" % (where, type(v).__name__))
        for k, x in v.items():
            if k in spec:
                _shape("%s.%s" % (path, k) if path else k, x, spec[k])


SECRET_PATTERNS = (
    (r"sk-[A-Za-z0-9_\-]{20,}", "an API key (sk-...)"), (r"AKIA[0-9A-Z]{16}", "an AWS access key"), (r"gh[pousr]_[A-Za-z0-9]{30,}", "a GitHub token"), (r"xox[abprs]-[A-Za-z0-9\-]{10,}", "a Slack token"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "a private key"), (r"(?i)bearer\s+[A-Za-z0-9._\-]{30,}", "a bearer token"), (r"AIza[0-9A-Za-z_\-]{35}", "a Google API key"), (r"csk-[A-Za-z0-9]{20,}", "a Cerebras API key"),
)


def scan_secrets(cfg):
    """a film shows every word you give it, and a film is published: a text that looks like a key or a token is refused, with where it is"""
    import re as _re

    def walk(o, path):
        if isinstance(o, str):
            for pat, what in SECRET_PATTERNS:
                if _re.search(pat, o):
                    refuse("%s contains what looks like %s: a film is shown in public. Remove it (replace it with ...) and build again" % (path or "the storyboard", what))
        elif isinstance(o, dict):
            for k, v in o.items():
                walk(v, "%s.%s" % (path, k) if path else k)
        elif isinstance(o, list):
            for j, v in enumerate(o):
                walk(v, "%s[%d]" % (path, j))
    walk(cfg, "")


def check_shapes(cfg):
    if not isinstance(cfg, dict):
        refuse("the storyboard must be a JSON object { ... }, not %s" % type(cfg).__name__)
    for k, spec in SHAPES.items():
        if k in cfg:
            _shape(k, cfg[k], spec)
    sc = cfg.get("scenes")
    if not isinstance(sc, list):
        refuse("scenes must be a list [ ... ] of scenes, not %s" % type(sc).__name__)
    if len(sc) > 60:
        refuse("a film has at most 60 scenes (this has %d)" % len(sc))
    for i, x in enumerate(sc):
        if not isinstance(x, dict):
            refuse("scene %d must be an object { \"scene\": ..., ... }, not %s" % (i, type(x).__name__))
        for k, v in x.items():
            if k in SCENE_SHAPES:
                _shape("scenes[%d].%s" % (i, k), v, SCENE_SHAPES[k])


def load(path):
    """read, shape-check and validate a storyboard; any leftover surprise becomes a refusal, never a traceback"""
    try:
        cfg = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        refuse("the storyboard is not readable JSON: %s" % e)
    check_shapes(cfg)
    scan_secrets(cfg)
    try:
        return _load(cfg)
    except Refusal:
        raise
    except (TypeError, AttributeError, KeyError, ValueError, IndexError) as e:
        refuse("a value in the storyboard has a shape the film cannot use (%s: %s); compare it with templates/agent-film/README.md or the template" % (type(e).__name__, e))


def _load(cfg):
    extra = set(cfg) - KEYS
    if extra:
        refuse("unknown key(s) %s (allowed: %s)" % (sorted(extra), sorted(KEYS)))
    for k in ("slug", "model", "scenes"):
        if k not in cfg:
            refuse("missing required key %r" % k)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", cfg["slug"]):
        refuse("slug: lowercase letters, digits and dashes")
    cfg.setdefault("prompt", "")   # the typed task is needed only by the scenes that show it (checked below)
    for k, v in DEFAULTS.items():
        if isinstance(v, dict):
            cfg[k] = {**v, **cfg.get(k, {})}
        else:
            cfg.setdefault(k, v)
    if "attachment" in cfg:
        at = cfg["attachment"]
        if not isinstance(at, dict) or set(at) - {"title", "meta", "thumb"} or not str(at.get("title", "")).strip():
            refuse('attachment is {"title": ..., "meta": ..., "thumb": <optional image path>} (optional: leave the key out for no attachment)')
        if at.get("thumb") and not os.path.exists(at["thumb"]):
            refuse("attachment thumb not found: %s" % at["thumb"])
    if cfg.get("timer") not in (None, True, False):
        refuse("timer is true or false (the elapsed-time pill centred in the title bar; off by default)")
    if cfg.get("partner_logo") and (not os.path.exists(cfg["partner_logo"]) or os.path.splitext(cfg["partner_logo"])[1].lower() not in (".svg", ".png", ".jpg", ".jpeg", ".webp")):
        refuse("partner_logo %s not found, or not an SVG, PNG, JPG or WebP image" % cfg["partner_logo"])
    if set(cfg.get("words") or {}) - set(WORDS_HELP):
        refuse("words keys are %s (unknown: %s)" % (sorted(WORDS_HELP), sorted(set(cfg["words"]) - set(WORDS_HELP))))
    cap = up_to(cfg["model"])
    if not cap and not (isinstance(cfg.get("claim"), dict) and "number" in cfg["claim"]) and any(x.get("scene") == "claim" for x in cfg["scenes"] if isinstance(x, dict)):
        refuse("%r has no stated speed in this kit, so a claim scene needs claim.number: the tokens a second YOU measured on Cerebras (never a number you were not given)" % cfg["model"])
    if cap:
        if float(cfg["claim"]["number"]) > cap:
            refuse("claim.number %s is above the %d tokens a second stated for %s: a film never claims more than the model's stated 'up to'" % (cfg["claim"]["number"], cap, cfg["model"]))
        mr = re.search(r"[\d,]+", str(cfg["meter"].get("rate", "")))
        if mr and int(mr.group().replace(",", "")) > cap:
            refuse("meter.rate %s is above the %d tokens a second stated for %s" % (cfg["meter"]["rate"], cap, cfg["model"]))
    if cfg["theme"] not in THEMES:
        refuse("theme %r is not one of %s" % (cfg["theme"], THEMES))
    if not cfg["scenes"]:
        refuse("scenes is empty")
    t = 0
    for i, sc in enumerate(cfg["scenes"]):
        bad = set(sc) - SCENE_KEYS
        if bad:
            refuse("scene %d: unknown key(s) %s" % (i, sorted(bad)))
        if sc.get("scene") in FUTURE_STATES:
            refuse("scene %d: %r is a planned state, not built yet: %s" % (i, sc["scene"], FUTURE_STATES[sc["scene"]]))
        if sc.get("scene") not in STATES:
            refuse("scene %d: %r is not one of %s" % (i, sc.get("scene"), tuple(STATES)))
        if i == 0 and not STATES[sc["scene"]]["start"]:
            refuse("scene 0: a film cannot START with %r (allowed first scenes: %s)" % (sc["scene"], tuple(k for k, v in STATES.items() if v["start"])))
        if i > 0:
            prev = cfg["scenes"][i - 1]["scene"]
            if sc["scene"] not in STATES[prev]["next"]:
                refuse("scene %d: %r cannot follow %r (after %r: %s)" % (i, sc["scene"], prev, prev, STATES[prev]["next"] or "nothing, it is the end"))
        if "ms" not in sc:   # a scene's length is DERIVED from what it holds unless you say otherwise (say it only to hold LONGER; the loader refuses shorter than the content needs)
            try:
                sc["ms"] = derive_ms(cfg, sc)
            except Refusal:
                raise
            except Exception as e:  # noqa: BLE001
                refuse("scene %d: ms is not given and cannot be derived for a %r scene yet (%s): give ms" % (i, sc.get("scene"), e))
        if not isinstance(sc.get("ms"), (int, float)) or sc["ms"] < 600:
            refuse("scene %d: ms must be a number of at least 600" % i)
        # a content key belongs to the scenes that draw it; anywhere else it would be silently ignored, so it is refused
        where = {"type_ms": ("typing",), "prompt": ("typing", "welcome", "turn", "answer", "versus"), "tool": ("turn", "answer"), "meter": ("turn", "answer"), "answer": ("answer", "versus"),
                 "claim": ("claim",), "thread": ("thread", "versus"), "tps": ("thread",), "versus": ("versus",), "clip_from": ("popin",), "variant": ("lockup",), "ask": ("ask",), "second": ("second-turn",), "integration": ("integration",), "browse": ("browse",), "intro": ("intro",)}
        for k, kinds in where.items():
            if k in sc and sc["scene"] not in kinds:
                refuse("scene %d: %r is a %s key and has no effect on a %r scene" % (i, k, "/".join(kinds), sc["scene"]))
        if sc["scene"] == "versus" and (sc.get("versus") or {}).get("view") == "answer" and "thread" not in sc:
            # view "answer": the house prompt bubble and answer card, drawn in both lanes (the same components as the turn and answer states, side by side)
            a_ = {**cfg["answer"], **sc.get("answer", {})}
            body_ = " ".join([a_["lead"]] + [(" ".join(b) if isinstance(b, list) else b) for b in a_["bullets"]])
            sc["thread"] = [{"kind": "user", "text": {**cfg, **{k: sc[k] for k in ("prompt",) if k in sc}}["prompt"]}, {"kind": "say", "who": cfg["model"], "text": body_}]
        if sc.get("cut") not in (None, True, False):
            refuse("scene %d: cut is true or false (a hard cut into the scene, no crossfade)" % i)
        if sc.get("cut") and i == 0:
            refuse("scene 0: nothing to cut from")
        if sc.get("cut") and cfg["scenes"][i - 1]["scene"] == "typing":
            refuse("scene %d: the scene after typing is entered by the composer's morph, which is not a cut" % i)
        if sc["scene"] == "lockup" and sc.get("variant", "partner") not in ("partner", "powered-by"):
            refuse("scene %d: lockup variant is partner (the two logos) or powered-by" % i)
        if sc["scene"] == "typing":
            click = sc["ms"] - CLICK_LEAD_MS; ptr = click - POINTER_MS; room = ptr - TYPE_GAP_MS - TYPE_START_MS
            if room < 600:
                refuse("scene %d: a typing scene needs at least %d ms (%d to type at least, %d before the pointer starts, the %d ms glide, the click %d ms before the end)" % (i, 600 + TYPE_START_MS + TYPE_GAP_MS + POINTER_MS + CLICK_LEAD_MS, 600, TYPE_GAP_MS, POINTER_MS, CLICK_LEAD_MS))
            if sc.get("type_ms", room) > room:
                refuse("scene %d: type_ms %s leaves no time for the pointer and the click; at most %d for a scene of %d ms" % (i, sc.get("type_ms"), room, sc["ms"]))
            sc["type_ms"] = int(sc.get("type_ms", room)); sc["click_at"] = click; sc["pointer_from"] = ptr
        if sc["scene"] in ("thread", "versus"):
            th = sc.get("thread")
            if not isinstance(th, list) or not th:
                refuse('scene %d: a %s scene needs "thread": [{"who": ..., "text": ...}, ...]' % (i, sc["scene"]))
            for j, m_ in enumerate(th):
                if not isinstance(m_, dict) or set(m_) - {"who", "text", "kind", "title", "verdict"}:
                    refuse("scene %d, message %d: keys are who, text, kind, title, verdict" % (i, j))
                if m_.get("kind", "say") not in THREAD_KINDS:
                    refuse("scene %d, message %d: kind %r is not one of %s" % (i, j, m_.get("kind"), THREAD_KINDS))
                if not str(m_.get("text", "")).strip():
                    refuse("scene %d, message %d: text is empty" % (i, j))
                if m_.get("kind", "say") == "say" and not str(m_.get("who", "")).strip():
                    refuse("scene %d, message %d: a say message needs who (the agent's name)" % (i, j))
        if sc["scene"] == "thread":
            tps = sc.get("tps", cfg["tps"])
            if cap and isinstance(tps, (int, float)) and tps > cap:
                refuse("scene %d: tps %s is above the %d tokens a second stated for %s" % (i, tps, cap, cfg["model"]))
            if not isinstance(tps, (int, float)) or tps < MIN_TPS:
                refuse("scene %d: a thread streams at the Cerebras rate, at least %d tokens a second (tps is %r). A slower rate is shown only as the GPU lane of a versus scene" % (i, MIN_TPS, tps))
            plan, need = thread_plan(cfg, sc)
            if sc["ms"] < need:
                refuse("scene %d: this thread needs at least %d ms (%d messages at %s tokens a second, %d ms between them, %d ms to settle); the scene is %d ms. Shorten it or lengthen the scene" % (i, need, len(sc["thread"]), tps, GAP_MS, SETTLE_MS, sc["ms"]))
        if sc["scene"] == "versus":
            v = {**VERSUS_DEFAULTS, **(sc.get("versus") or {})}
            if set(sc.get("versus") or {}) - set(VERSUS_DEFAULTS):
                refuse("scene %d: versus keys are %s" % (i, sorted(VERSUS_DEFAULTS)))
            if not isinstance(v["cerebras_tps"], (int, float)) or v["cerebras_tps"] < MIN_TPS:
                refuse("scene %d: the Cerebras lane streams at least %d tokens a second (cerebras_tps is %r): it is never slow, in a re-render or anywhere else" % (i, MIN_TPS, v["cerebras_tps"]))
            if not cap and "cerebras_tps" not in (sc.get("versus") or {}):
                refuse("scene %d: %r has no stated speed in this kit, so versus needs cerebras_tps: the tokens a second you measured on Cerebras (at least %d)" % (i, cfg["model"], MIN_TPS))
            if cap and v["cerebras_tps"] > cap:
                refuse("scene %d: cerebras_tps %s is above the %d tokens a second stated for %s" % (i, v["cerebras_tps"], cap, cfg["model"]))
            if not isinstance(v["gpu_tps"], (int, float)) or not 0 < v["gpu_tps"] < v["cerebras_tps"]:
                refuse("scene %d: gpu_tps must be a number above 0 and below cerebras_tps" % i)
            rg = v.get("gpu_tps_range")
            if rg is not None:
                if len(rg) != 2 or not 0 < rg[0] <= v["gpu_tps"] <= rg[1] < v["cerebras_tps"]:
                    refuse("scene %d: versus.gpu_tps_range is [low, high] tokens a second across GPU providers, with low <= gpu_tps <= high < cerebras_tps (the lane streams at gpu_tps; the range is printed beside it)" % i)
            if not str(v.get("note", "")).strip():
                refuse('scene %d: versus needs a "note": where the GPU rate comes from, or that it is illustrative (it is printed on the film)' % i)
            if v["fast_forward"] and (not isinstance(v["fast_forward"], (int, float)) or v["fast_forward"] <= 1):
                refuse("scene %d: versus.fast_forward is a speed-up above 1 (5 is the source video's), or 0 for none" % i)
            sc["versus"] = v
            plan, need = lane_plan(sc, v["cerebras_tps"])
            vt = versus_times(sc)
            gneed = vt["g_film_end"] + DONE_HOLD_MS
            if sc["ms"] < gneed:
                refuse("scene %d: the GPU lane finishes at %d ms and both DONE cards must stay up for %d ms after it, so the scene needs at least %d ms; it is %d ms" % (i, vt["g_film_end"], DONE_HOLD_MS, gneed, sc["ms"]))
            if sc["ms"] < need:
                refuse("scene %d: the Cerebras lane needs at least %d ms (%d messages at %s tokens a second); the scene is %d ms" % (i, need, len(sc["thread"]), v["cerebras_tps"], sc["ms"]))
        if sc["scene"] == "intro":
            q = sc.get("intro") or {}
            if set(q) - {"title", "description", "logo", "lockup"} or not str(q.get("title", "")).strip() or not str(q.get("description", "")).strip():
                refuse('scene %d: intro is {"title": the project\'s name, "description": what it is and does, "logo": an image path (optional), "lockup": false to hide the Cerebras x model logos under the description}: a title and a description, no bullet points' % i)
            if q.get("logo") and (not os.path.exists(q["logo"]) or os.path.splitext(q["logo"])[1].lower() not in (".svg", ".png", ".jpg", ".jpeg", ".webp")):
                refuse("scene %d: intro logo %s not found, or not an SVG, PNG, JPG or WebP image" % (i, q["logo"]))
            if sc["ms"] < intro_times(q)["end"] + INTRO_HOLD_MS:
                refuse("scene %d: the intro slide needs at least %d ms (it builds up for %d ms and must then hold %d ms to be read); it is %d ms" % (i, intro_times(q)["end"] + INTRO_HOLD_MS, intro_times(q)["end"], INTRO_HOLD_MS, sc["ms"]))
        if sc["scene"] == "ask":
            q = sc.get("ask") or {}
            if set(q) - {"question", "options", "reply"} or not str(q.get("question", "")).strip() or not str(q.get("reply", "")).strip():
                refuse('scene %d: ask is {"question": ..., "options": [..] (optional), "reply": the user\'s answer}' % i)
            t0, t1, t2 = ask_times(q)
            if sc["ms"] < t2 + 1500:
                refuse("scene %d: the ask scene needs at least %d ms (question %d ms, options, the reply at %d ms, then 1500 ms for the turn to start); it is %d ms" % (i, t2 + 1500, t1 - t0, t2, sc["ms"]))
        if sc["scene"] == "second-turn":
            q = sc.get("second") or {}
            if set(q) - {"prompt"} or not str(q.get("prompt", "")).strip():
                refuse('scene %d: second is {"prompt": the second prompt}' % i)
            click = sc["ms"] - 1500; ptr = click - POINTER_MS; room = ptr - TYPE_GAP_MS - 600
            if room < 600:
                refuse("scene %d: a second-turn scene needs at least %d ms (type, the %d ms glide, the click, 1500 ms after it)" % (i, 600 + TYPE_GAP_MS + 600 + POINTER_MS + 1500, POINTER_MS))
            sc["click_at"] = click; sc["pointer_from"] = ptr; sc["type_ms"] = int(room)
            sc["second"]["type_ms"] = int(room)
        if sc["scene"] == "integration":
            q = sc.get("integration") or {}
            if set(q) - {"tag", "title", "badge", "chips", "body"} or not str(q.get("title", "")).strip():
                refuse('scene %d: integration is {"tag": ..., "title": ..., "badge": ..., "chips": [..], "body": [lines]}' % i)
            if sc["ms"] < integration_times(q)["end"] + 1500:
                refuse("scene %d: the integration scene needs at least %d ms (defocus, the card building, the text streaming, 1500 ms to hold); it is %d ms" % (i, integration_times(q)["end"] + 1500, sc["ms"]))
        if sc["scene"] == "browse":
            q = sc.get("browse") or {}
            pages = q.get("pages")
            if set(q) - {"pages"} or not isinstance(pages, list) or not pages:
                refuse('scene %d: browse is {"pages": [{"url": ..., "title": ..., "heading": ..., "lines": [..], "button": ..., "scroll": px, "modal": {"title": ..., "buttons": [..]}, "pointer": true, "ms": ...}]}' % i)
            for j, pg in enumerate(pages):
                if set(pg) - {"url", "title", "heading", "lines", "button", "scroll", "modal", "pointer", "ms"} or not pg.get("url") or not pg.get("heading"):
                    refuse("scene %d, page %d: keys are url, title, heading, lines, button, scroll, modal, pointer, ms (url and heading are required)" % (i, j))
            if sc["ms"] < 1100 + 1200 * len(pages) + 600:
                refuse("scene %d: a browse scene with %d pages needs at least %d ms (the pane opens in 1100, 1200 a page, 600 to hold)" % (i, len(pages), 1100 + 1200 * len(pages) + 600))
        if sc["scene"] == "popin" and (not isinstance(sc.get("clip_from", 0), (int, float)) or sc.get("clip_from", 0) < 0):
            refuse("scene %d: clip_from is a number of milliseconds into the clip, 0 or more" % i)
        if sc["scene"] == "answer":
            st = int({**cfg["answer"], **sc.get("answer", {})}.get("stream_ms", 0))
            at = answer_tokens({**cfg["answer"], **sc.get("answer", {})})
            if st and at * 1000 < st * MIN_TPS:
                refuse("scene %d: answer.stream_ms is %d for about %d tokens, which is %d tokens a second; a streamed answer is at least %d (stream_ms %d or less, or write more)" % (i, st, at, at * 1000 // st, MIN_TPS, at * 1000 // MIN_TPS))
            if st < 0 or (st and st > sc["ms"] - 1600):
                refuse("scene %d: answer.stream_ms is %d but the scene is %d ms; the stream starts at 500 ms and the card must hold for 1100 ms after it" % (i, st, sc["ms"]))
        sc["start"] = t
        sc["i"] = i
        t += sc["ms"]
    cfg["duration"] = t
    if not str(cfg["prompt"]).strip():
        needs = [i for i, x in enumerate(cfg["scenes"]) if x["scene"] in PROMPT_SCENES and not x.get("prompt")]
        if needs:
            refuse("scene %d (%s) shows the user's typed task but the film has no `prompt`: give the task in the user's words" % (needs[0], cfg["scenes"][needs[0]]["scene"]))
    if any(s["scene"] == "popin" for s in cfg["scenes"]):
        if "popin" not in cfg or "video" not in cfg["popin"]:
            refuse('a popin scene needs "popin": {"video": "<path to your video>"}')
        if not os.path.exists(cfg["popin"]["video"]):
            refuse("popin video not found: %s" % cfg["popin"]["video"])
    return cfg


def num(text, delay=450, dur=1400):
    """a number DIALS up to its final value when its scene appears: the leading number of `text` becomes a counting span (film.js, data-count), the rest stays"""
    m = re.match(r"^([\d,]*\.?\d+)(.*)$", str(text), re.S)
    if not m:
        return esc(text)
    raw = m.group(1)
    dec = len(raw.split(".")[1]) if "." in raw else 0
    val = float(raw.replace(",", ""))
    return '<span data-count="%s" data-dec="%d" data-delay="%d" data-dur="%d">%s</span>%s' % (val, dec, delay, dur, esc(raw), esc(m.group(2)))


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ── the scenes ──────────────────────────────────────────────────────────────────────────────────────────────────
MEASURED = {}   # what tools/agent-film-measure.mjs measured in a real Chrome (see main()): the click targets, the typed prompt's height, where the answer card ends. Empty on the first pass: the fallbacks below are the layout's designed numbers


def measured(key, default):
    return MEASURED.get(key, default)


TIMER = [None]   # (from, stop) in film time while the OPTIONAL timer pill is on


def timer_pill():
    """the elapsed-time pill centred in the title bar (reference video 3): counts from the first turn, stops where the answer begins; only when the storyboard says timer: true"""
    if not TIMER[0]:
        return ""
    f, st = TIMER[0]
    return (f'<span class="ag-chip" style="position:absolute;left:50%;top:26px;transform:translateX(-50%);height:30px;padding:0 14px;border-radius:15px;font-size:15px;z-index:3">'
            f'<b data-timer data-from="{f}" data-stop="{st}" style="font-weight:600">0.0s</b></span>')


def window(body, bar=True, timer=False):
    return Pg.shell(156, 44, 1608, 992, 20, (A.titlebar(True, cfg_model[0]) if bar else "") + (timer_pill() if timer else "") + body)


def docked(state, x=372, y=868, w=860):
    if state == "stop":
        mid = f'{A.model_pill(16, True, "var(--ink-3)", cfg_model[0])}<span class="ag-send stop" style="width:36px;height:36px">{A.ic("stop", 20)}</span>'
    else:
        mid = (f'{A.model_pill(16, False, "var(--ink-2)", cfg_model[0])}'
               f'<span class="ag-send off" style="width:36px;height:36px">{A.ic("up", 18, 2.2)}</span>')
    return (f'<div class="ag-composer" style="left:{x}px;top:{y - 44}px;width:{w}px;height:112px;border-radius:20px;box-shadow:none;border:1px solid var(--line);background:var(--card-2)">'
            f'<div class="ag-text" style="padding:16px 16px;font-size:19px;line-height:26px"><span class="ag-ph">Message Cerebras</span></div>'
            f'<div class="ag-bar" style="left:16px;right:11px;bottom:10px;height:36px;gap:16px"><span style="color:var(--ink-2)">{A.ic("plus", 22, 1.6)}</span><span style="flex:1"></span>{mid}</div></div>'
            f'<span style="position:absolute;left:{x + w // 2 - 22}px;top:{y - 44 + 112}px;width:44px;height:8px;border-radius:4px;background:#8c8c8a"></span>')


ATTACH = [""]   # the optional attachment card, drawn under the user's bubble in the turn and answer scenes


def bubble(text, right=376, top=111):
    return (f'<div style="position:absolute;right:{right}px;top:{top}px;display:flex;flex-direction:column;align-items:flex-end"><div class="ag-bubble" style="position:static;width:auto;max-width:600px;padding:18px 20px;font-size:16.5px;line-height:24px;border-radius:20px;text-align:left">{esc(text)}</div>{ATTACH[0]}</div>')


def chat_x(cfg):
    return 372


def _popin(cfg):
    return any(s["scene"] == "popin" for s in cfg["scenes"])



THREAD_KINDS = ("say", "tool", "user")
GAP_MS = 650           # the pause between one message and the next
FIRST_MS = 700         # the pause before the first message
SETTLE_MS = 900
MODEL_UP_TO = {"kimi": 1000}   # the speed STATED for a model, "up to N tokens per second" (owner, 2026-11-20: Kimi is up to 1,000): a film for that model never claims, streams or shows a Cerebras lane above it, and never below MIN_TPS, so a Kimi film runs at exactly 1,000
MIN_TPS = 1000         # the Cerebras speed: nothing the film streams as Cerebras is slower than this (refused in load(), held again by tools/agent-film-verify.mjs)
# THE PHYSICAL BEATS OF A CLICK, fixed for every theme so no storyboard has to ask: the typing scene ends with the pointer gliding to the send button and pressing it; the morph begins at the click
POINTER_MS = 700       # the pointer's glide to the send button
CLICK_LEAD_MS = 300    # the click is this long before the scene ends (the morph, MORPH_PRE in film.js, starts at the click)
TYPE_START_MS = 250    # typing begins this long into the scene
TYPE_GAP_MS = 150      # the pause between the last typed character and the pointer's start
PRESS_MS = 140         # how long the send button stays pressed
THINK_FROM = 100       # the first message of a thread is on screen from here, FIRST_MS is when the first word streams: the beat between is the thinking row
THINK_MS = 600         # the "thinking" row (the next section's title and three pulsing dots) shows this long before a message starts
FF_LEAD_MS = 800       # the slow lane's fast-forward badge arrives this long after the fast lane is done
LANE_GAP_MS = 0        # no pause between a lane's messages: a lane's time is exactly tokens / tokens-a-second (the maths on screen must match)
PROMPT_SCENES = ("typing", "welcome", "turn", "answer", "ask", "second-turn", "integration", "browse")   # scenes that draw the typed task
INTRO_HOLD_MS = 2200   # an intro slide holds this long after it has built up, so it can be read
DONE_HOLD_MS = 3000    # the source video holds both DONE cards for seconds: the Cerebras one never goes, the GPU one arrives and both stay on screen at least this long
VERSUS_DEFAULTS = {"gpu_tps": 60, "gpu_tps_range": None, "cerebras_tps": 1000, "gpu_label": "GPU Inference", "cerebras_label": "Cerebras (WSE)", "note": "", "view": "thread", "fast_forward": 0}        # a thread scene must leave this long, after its last message, to hold


def eff(cfg, sc):
    """the film's content with this scene's own overrides laid over it (prompt, tool, meter, answer, claim)"""
    out = dict(cfg)
    for k in ("prompt", "tool", "meter", "answer", "claim"):
        if k in sc:
            out[k] = {**cfg[k], **sc[k]} if isinstance(cfg[k], dict) else sc[k]
    return out


def split_words(text):
    return [w for w in re.split(r"\s+", str(text).strip()) if w]


def reveal(parts, delay, dur, tag="span", style=""):
    """text that STREAMS in word by word between delay and delay+dur (ms from the scene's start): film.js shows the first k words, a function of the time. Every word is laid out
    from the start (hidden, not absent), so nothing jumps as it arrives. parts: [(text, bold)]"""
    n = sum(len(split_words(t)) for t, _ in parts)
    inner = ""
    for text, bold in parts:
        ws = "".join('<span class="w">%s </span>' % esc(w) for w in split_words(text))
        inner += "<b>%s</b>" % ws if bold else ws
    return '<%s data-reveal data-reveal-delay="%d" data-reveal-ms="%d" data-words="%d"%s>%s</%s>' % (tag, delay, max(1, dur), n, (' style="%s"' % style) if style else "", inner, tag)


def ntok(text):
    """tokens in a text: an ESTIMATE, four thirds of the words (the film has no tokenizer); the same estimate is used for every lane so the comparison is the rates'"""
    return -(-len(split_words(text)) * 4 // 3)


def answer_tokens(a):
    return ntok(" ".join([a["lead"]] + [(" ".join(b) if isinstance(b, list) else b) for b in a["bullets"]]))


def _plan(msgs, tps, gap):
    """THE MATHS, exact: a message starts when the tokens before it have been streamed and ends when its own are, so start = FIRST_MS + (gaps so far) + round(tokens_before / tps * 1000) and the lane ends at FIRST_MS + round(all_tokens / tps * 1000) plus its gaps. With gap 0 (the versus lanes) the lane's time is EXACTLY tokens / tps: no pause is ever counted into a speed. A message with a `title` streams the title first (its tokens count). The first message, if it is the user's, is on screen at THINK_FROM so there is a beat of "thinking" before the first word. Returns (plan, the end of the last message)."""
    cum, extra, plan = 0, 0, []
    ms = lambda c: int(c * 1000.0 / tps + 0.5)
    for i, m in enumerate(msgs):
        user = m.get("kind") == "user"
        kt = ntok(m["title"]) if m.get("title") and not user and m.get("kind") != "tool" else 0
        kb = 0 if user else ntok(m["text"])
        s0 = FIRST_MS + extra + ms(cum)
        cum += kt
        smid = FIRST_MS + extra + ms(cum)
        cum += kb
        s1 = FIRST_MS + extra + ms(cum)
        plan.append({**m, "start": (THINK_FROM if (user and i == 0) else s0), "mid": smid, "dur": 0 if not (kt + kb) else max(1, s1 - s0), "tdur": max(1, smid - s0) if kt else 0, "bdur": max(1, s1 - smid) if kb else 0,
                     "n": len(split_words(m["text"])) + (len(split_words(m["title"])) if kt else 0), "tok": kt + kb, "s0": s0})
        extra += gap
    return plan, FIRST_MS + extra - gap + ms(cum)


def thread_plan(cfg, sc):
    """the schedule of a thread scene, worked out and checked here, not in the browser: each message starts after the last has finished streaming (tokens / tps) plus GAP_MS"""
    plan, end = _plan(sc["thread"], float(sc.get("tps", cfg["tps"])), GAP_MS)
    return plan, end + SETTLE_MS


def lane_plan(sc, tps):
    plan, end = _plan(sc["thread"], float(tps), LANE_GAP_MS)
    return plan, end + SETTLE_MS


def versus_times(sc):
    """both lanes' schedules in one place: the Cerebras lane in film time, the GPU lane in LANE time (its own clock), and the film time the GPU lane's end falls at once the fast-forward (if any) has begun: the slow lane runs `fast_forward` times faster from FF_LEAD_MS after the fast lane is done, and everything it shows (text, token count, clock) follows that clock"""
    v = sc["versus"]
    cplan, c_end = _plan(sc["thread"], float(v["cerebras_tps"]), LANE_GAP_MS)
    gplan, g_end = _plan(sc["thread"], float(v["gpu_tps"]), LANE_GAP_MS)
    ff = v.get("fast_forward") or 0
    ff_at = c_end + FF_LEAD_MS
    on = bool(ff) and g_end > ff_at + 600
    film = lambda L: int(round(L if not on or L <= ff_at else ff_at + (L - ff_at) / ff))
    return {"cplan": cplan, "gplan": gplan, "c_end": c_end, "g_end": g_end, "ff": ff if on else 0, "ff_at": ff_at, "g_film_end": film(g_end), "film": film}


GENERIC_AVATAR = '<span style="display:inline-flex;width:20px;height:20px;border-radius:6px;border:2px solid var(--ink-3);box-sizing:border-box"></span>'   # the competitor lane's avatar: a plain outlined square, no brand and certainly not the Cerebras mark
DOTS = '<span data-dots style="display:inline-flex;gap:4px;margin-left:4px">' + "".join('<i style="width:5px;height:5px;border-radius:50%;background:var(--ink-3);display:block"></i>' for _ in range(3)) + '</span>'


def attach_card(cfg, width=300):
    """the OPTIONAL attachment as a card (under the user's bubble); with no thumb a plain page is drawn (a warm sheet with faint text lines) and nothing pretends to be a document image"""
    at = cfg.get("attachment")
    if not at:
        return ""
    if at.get("thumb"):
        import base64, mimetypes
        mt = mimetypes.guess_type(at["thumb"])[0] or "image/png"
        pg = 'background:url(data:%s;base64,%s) center/cover' % (mt, base64.b64encode(open(at["thumb"], "rb").read()).decode())
    else:
        pg = "background:repeating-linear-gradient(#e6dfd5 0 2px,transparent 2px 8px) 8px 12px/28px 100% no-repeat,#f6f1e9"
    return (f'<div class="att-card" style="display:flex;align-items:center;gap:12px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:9px 14px 9px 10px;margin-top:10px;width:{width}px;box-sizing:border-box">'
            f'<span style="width:44px;height:54px;border-radius:5px;border:1px solid var(--line);flex:none;{pg}"></span>'
            f'<span><span style="display:block;font-size:14px;font-weight:600;color:var(--ink)">{esc(at["title"])}</span>'
            f'<span style="display:block;margin-top:3px;font-family:var(--font-mono);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3)">{esc(at.get("meta", ""))}</span></span></div>')


def thread_rows(plan, w=860, bubble_max=600, avatar=None, attach=""):
    rows = ""
    first_user = True
    prev_start = THINK_FROM
    for i, m_ in enumerate(plan):
        kind_m = m_.get("kind", "say")
        who = avatar or A.mark(20)
        if kind_m == "user":
            card = attach if first_user else ""
            first_user = False
            rows += (f'<div data-reveal data-reveal-delay="{m_["start"]}" data-reveal-ms="1" data-words="{m_["n"]}" style="display:flex;flex-direction:column;align-items:flex-end;margin:0 0 18px">'
                     f'<div class="ag-bubble" style="position:static;width:auto;max-width:600px;padding:18px 20px;font-size:16.5px;line-height:24px;border-radius:20px;text-align:left">'
                     + "".join('<span class="w">%s </span>' % esc(w) for w in split_words(m_["text"])) + '</div>' + card + '</div>')
        elif kind_m == "tool":
            rows += (f'<div data-appear="{m_["start"]}" style="display:flex;align-items:center;gap:10px;margin:0 0 16px 4px;color:var(--ink-3);font-size:14px">' + f'<span style="color:var(--ink-2)">{A.ic("browser", 18, 1.7)}</span>'
                     + reveal([(m_["text"], False)], m_["start"], m_["dur"], style="display:block") + f'<span style="color:var(--ink-3)">{A.ic("fwd", 13, 2)}</span></div>')
        else:
            # a "thinking" row first, where there is time for one: the next section's title (or Thinking) and three pulsing dots, gone the moment the message begins
            tf = max(prev_start, m_["start"] - THINK_MS)
            if tf < m_["start"] and (i == 0 or m_.get("title") or plan[i - 1].get("kind") == "user"):
                rows += (f'<div data-think data-think-from="{tf}" data-think-to="{m_["start"]}" style="display:flex;align-items:center;gap:8px;margin:0 0 18px 0;color:var(--ink-3);font-size:13px;font-weight:600">{who}<span>{esc(m_.get("title") or "Thinking")}</span>{DOTS}</div>')
            verdict = bool(m_.get("verdict"))
            tag = '<span style="margin-left:auto;font-family:var(--font-mono);font-size:10.5px;letter-spacing:.08em;color:var(--accent);border:1px solid var(--accent);border-radius:4px;padding:2px 6px">FINAL ANSWER</span>' if verdict else ""
            head = f'<div style="display:flex;align-items:center;gap:8px;margin:0 0 6px 2px;color:var(--ink-3);font-size:13px;font-weight:600">{who}<span>{esc(m_["who"])}</span>{tag}</div>'
            body = ""
            if m_.get("title"):
                body += reveal([(m_["title"], True)], m_["start"], m_["tdur"] or 1, tag="div", style=f'margin:0 0 4px;font-size:17px;{"color:var(--accent);" if verdict else ""}')
            body += reveal([(m_["text"], False)], m_["mid"], m_["bdur"] or 1, tag="div" if m_.get("title") else "span")
            card_style = ("position:static;padding:14px 18px;font-size:16.5px;line-height:24px;background:var(--card);border-inline-start:4px solid var(--accent);border-radius:4px 14px 14px 4px;box-shadow:0 1px 0 var(--line)" if verdict
                          else "position:static;padding:14px 18px;font-size:16.5px;line-height:24px;background:var(--card-3)")
            rows += f'<div data-appear="{m_["start"]}" style="margin:0 0 18px">{head}<div class="ag-order" style="{card_style}">{body}</div></div>'
        prev_start = m_["start"]
    return rows


def partner_html(cfg, h):
    """the partner's logo beside Cerebras: the user's `partner_logo`; else Kimi's when the model is Kimi; else NOTHING (no other model's logo is in this kit, and a wrong logo is worse than none)"""
    if cfg.get("partner_logo"):
        return logo_html(cfg["partner_logo"], h)
    if "kimi" in str(cfg.get("model", "")).lower() and os.path.exists(os.path.join(ROOT, "kits", "kimi", "brand", "kimi_logo.svg")):
        return A.logo(h, partner_svg(cfg), "ag-logo-partner")   # Kimi's logo ships only where the Kimi kit does (a public checkout without it shows Cerebras alone, never a stand-in passed off as Kimi)
    return ""


def logo_html(path, h):
    """a user's logo: an SVG (inlined like the house marks) or a PNG, JPG or WebP (embedded as it is, at the given height)"""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".svg":
        return A.logo(h, build.inline_file(ROOT, path), "ag-logo-partner")
    import base64
    mt = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(ext)
    return '<img alt="" style="height:%dpx;width:auto;display:block" src="data:%s;base64,%s">' % (h, mt, base64.b64encode(open(path, "rb").read()).decode())


def intro_times(q):
    """the intro slide's clock, ms from its start: the title streaming from 350 at the Cerebras rate (its tokens in ms), the description 300 ms after the title, the Cerebras x model logos (unless `lockup` is false) 400 ms after the description; `end` is when everything is up. An intro is a title and a description (and the logos): nothing else"""
    t = 350
    title = (t, max(1, ntok(q["title"]))); t += title[1] + 300
    desc = (t, max(1, ntok(q["description"]))); t += desc[1]
    lock = t + 400 if q.get("lockup", True) else None
    return {"title": title, "description": desc, "lockup": lock, "end": (lock + 300) if lock else t}


def ask_times(q):
    """the ask scene's clock, in ms from the scene's start: the question streams at the Cerebras rate from 500 (so it takes exactly its tokens in ms), each option appears 250 ms after the last, the user's reply 800 ms after the last option"""
    t0 = 500
    t1 = t0 + max(1, ntok(q["question"]))
    opts = [t1 + 250 * (j + 1) for j in range(len(q.get("options") or []))]
    t2 = (opts[-1] if opts else t1) + 800
    return t0, t1, t2


def integration_times(q):
    """the integration card's clock: defocus 0 to 700, the card at 900, the title streaming from 1000 at the Cerebras rate, then the badge and chips (250 apart), then the body lines one after the other"""
    t = 1000; k = ntok(q["title"]); title = (t, max(1, k)); t += max(1, k) + 250
    badge = t if q.get("badge") else None
    if badge: t += 250
    chips = []
    for _ in q.get("chips") or []:
        chips.append(t); t += 250
    body = []
    for ln in q.get("body") or []:
        k = max(1, ntok(ln)); body.append((t, k)); t += k + 200
    return {"title": title, "badge": badge, "chips": chips, "body": body, "end": t}


def static_answer_card(cfg):
    a = cfg["answer"]
    lead = esc(a["lead"])
    bl = "".join("<li style='margin-top:6px'>" + (("<b>%s</b> %s" % (esc(b[0]), esc(b[1]))) if isinstance(b, list) else esc(b)) + "</li>" for b in a["bullets"])
    return (f'<div class="ag-order" style="position:static;padding:16px 20px 18px;font-size:16.5px;line-height:24px;background:var(--card-3)">{lead}'
            + (f'<ul style="margin-top:10px">{bl}</ul>' if bl else "") + '</div>')


def prior_rows(cfg, appear=0):
    """the first exchange as the context of a later state: the user's bubble (and the optional attachment), 'Worked for N seconds', the answer card; all complete"""
    a = cfg["answer"]
    return (f'<div data-appear="{appear}" style="display:flex;flex-direction:column;align-items:flex-end;margin:0 0 18px"><div class="ag-bubble" style="position:static;width:auto;max-width:600px;padding:18px 20px;font-size:16.5px;line-height:24px;border-radius:20px;text-align:left">{esc(cfg["prompt"])}</div>{ATTACH[0]}</div>'
            f'<div data-appear="{appear}" style="display:flex;align-items:center;gap:10px;margin:0 0 12px;color:var(--ink-3);font-size:13.5px;border-bottom:1px solid var(--line);padding-bottom:10px">{A.mark(24)}<span>Worked for {a["footer_seconds"]} seconds</span>{A.ic("fwd", 13, 2)}</div>'
            f'<div data-appear="{appear}" style="margin:0 0 18px">{static_answer_card(cfg)}</div>')


def status_row(at, until=None, label="Preparing this turn..."):
    """the loader row: there from `at`; with `until` it goes (opacity, its room stays) just before the scene crossfades out, so two scenes' loaders are never on screen together"""
    return (f'<div data-appear="{at}"{(" data-vanish=%d" % until) if until else ""} style="display:flex;align-items:center;gap:8px;margin:0 0 18px;color:var(--ink-3);font-size:14.5px"><span class="ag-spin" style="display:block;color:var(--ink-3)">{A.ic("ring", 20, 2)}</span>'
            f'<span>{esc(label)} <span data-elapsed data-from="{at}">1s</span></span></div>')


def pointer_html(frm, ms, click, x0, y0, x1, y1):
    return (f'<div class="ag-pointer" data-from="{frm}" data-ms="{ms}" data-click="{click}" data-x0="{x0:.1f}" data-y0="{y0:.1f}" data-x1="{x1:.1f}" data-y1="{y1:.1f}" '
            f'style="position:absolute;left:0;top:0;width:34px;height:42px;z-index:9;display:none;pointer-events:none"><svg viewBox="0 0 26 32" width="34" height="42"><path d="M2 1.5 L2 24 L8.2 18.4 L12.4 29 L16.8 27.2 L12.6 16.8 L21 16.6 Z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg></div>')


def scene_html(cfg, sc, theme):
    kind = sc["scene"]
    cfg = eff(cfg, sc)
    m = cfg["meter"]
    if kind == "typing":
        # THE CLICK, the same for every theme: the send button is disabled-grey until the first character, the pointer glides in from below after the last, the button presses (0.86 for PRESS_MS), the caret stops; the composer's morph starts at the click
        send = f'<span class="ag-send off" data-send data-press="{sc["click_at"]}" style="width:66px;height:66px;color:var(--card)">{A.ic("up", 30, 2.2)}</span>'
        mt = MEASURED.get("typing:%d" % sc["i"])
        H = max(230, int(mt["text_h"]) + 74) if mt else 230   # the composer is as tall as its typed prompt needs (the bar zone is 74 px), kept centred on the frame
        top = 140 - H // 2
        x1, y1 = (mt["tx"], mt["ty"]) if mt else (1511 + 66 * .78, top + H - 21 - 66 + 66 * .62)
        ptr = (f'<div class="ag-pointer" data-from="{sc["pointer_from"]}" data-ms="{POINTER_MS}" data-click="{sc["click_at"]}" data-x0="{x1 + 80:.1f}" data-y0="{y1 + 330:.1f}" data-x1="{x1:.1f}" data-y1="{y1:.1f}" '
               f'style="position:absolute;left:0;top:0;width:34px;height:42px;z-index:9;display:none;pointer-events:none"><svg viewBox="0 0 26 32" width="34" height="42"><path d="M2 1.5 L2 24 L8.2 18.4 L12.4 29 L16.8 27.2 L12.6 16.8 L21 16.6 Z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg></div>')
        att = cfg.get("attachment")
        stack = ""
        if att:
            stack = ('<div class="att-stack" data-slide-from="600" data-slide-ms="550" style="position:absolute;right:140px;top:22px;width:110px;height:112px">'
                     + "".join(f'<span class="att-page" style="position:absolute;left:{k * 8}px;top:{k * 5}px;width:80px;height:100px;border-radius:7px;border:1px solid var(--line);background:#f6f1e9;box-shadow:0 2px 6px rgba(0,0,0,.08);transform:rotate({(k - 1) * 4}deg)"></span>' for k in (2, 1, 0))
                     + f'<span class="att-page" style="position:absolute;left:0;top:0;width:80px;height:100px;border-radius:7px;border:1px solid var(--line);background:repeating-linear-gradient(#e6dfd5 0 2px,transparent 2px 8px) 10px 14px/60px 100% no-repeat,#f6f1e9"></span></div>')
        pad = "padding:29px 260px 29px 33px" if att else "padding:29px 33px"
        return Pg.place(150, 400, f'''<div class="ag-composer" style="position:absolute;left:24px;top:{top}px;width:1572px;height:{H}px;border-radius:40px;border-width:2px">
  <div class="ag-text" style="{pad};font-size:33px;line-height:49px"><span data-type="{esc(cfg["prompt"])}" data-type-ms="{sc["type_ms"]}"></span><span class="ag-caret" data-caret-until="{sc["click_at"]}"></span></div>{stack}
  <div class="ag-bar" style="left:30px;right:19px;bottom:21px;height:66px;gap:32px"><span style="color:var(--ink)">{A.ic("plus", 44, 2)}</span><span style="flex:1"></span>
    <span style="display:flex;align-items:center;gap:20px">{A.model_pill(26, False, "var(--ink-2)", cfg["model"])}</span>{send}</div></div>{ptr}''')
    if kind == "welcome":
        send = f'<span class="ag-send idle" style="width:38px;height:38px">{A.ic("up", 20, 2.2)}</span>'
        body = (f'<span style="position:absolute;left:772px;top:172px">{A.mark(52)}</span><div class="ag-welcome-h" style="top:262px;font-size:42.5px">What would you like to do?</div>'
                f'<div class="ag-composer" style="left:372px;top:371px;width:860px;height:128px;border-radius:22px;box-shadow:none;background:var(--card-2)">'
                f'<div class="ag-text" style="padding:16px 16px;font-size:18px;line-height:27px">{esc(cfg["prompt"])}</div>'
                f'<div class="ag-bar" style="left:16px;right:12px;bottom:10px;height:38px;gap:22px"><span style="color:var(--ink-2)">{A.ic("plus", 22, 1.8)}</span><span style="flex:1"></span>{A.model_pill(15, False, "var(--ink-2)", cfg["model"])}{send}</div></div>'
                f'<span style="position:absolute;left:782px;top:970px;width:44px;height:8px;border-radius:4px;background:#8c8c8a"></span>')
        return Pg.place(156, 44, '<div class="ag-window" style="left:0;top:0;width:1608px;height:992px;border-radius:20px;border:0;box-shadow:none">' + A.titlebar(False, cfg["model"]) + body + "</div>")
    if kind == "popin":
        # THE WHOLE WINDOW IS THE USER'S VIDEO: a 16:9 clip with rounded corners where the white window would be, on the ground. No chat, no pane, no chrome: the house styling is the
        # text states around it (the typed prompt, the claim, the lockup). The clip is cropped to fill (cover) if it is not exactly 16:9.
        return Pg.place(156, 87, '<div class="popin-card" style="width:1608px;height:905px;border-radius:20px;overflow:hidden;box-shadow:var(--shadow);background:#000"><img data-popin data-clip-from="%d" alt="" style="display:block;width:100%%;height:100%%;object-fit:cover"></div>' % int(sc.get("clip_from", 0)))
    if kind == "thread":
        cx = chat_x(cfg)
        plan, _ = thread_plan(cfg, sc)
        rows = thread_rows(plan, attach=attach_card(cfg))
        view = (f'<div style="position:absolute;left:{cx}px;top:96px;width:860px;height:740px;overflow:hidden"><div class="thread-in" data-view="740" style="position:relative">{rows}</div></div>')
        return window(view + docked("stop"), timer=True)
    if kind == "versus":
        v = sc["versus"]
        vt = versus_times(sc)
        PW, PH, TOP, VIEW = 760, 790, 112, 540
        out = ""
        for side, x, tps, label in (("cerebras", 36, v["cerebras_tps"], v["cerebras_label"]), ("gpu", 812, v["gpu_tps"], v["gpu_label"])):   # Cerebras on the LEFT, as lane A is in the source video (layouts/comparison)
            plan, end = (vt["cplan"], vt["c_end"]) if side == "cerebras" else (vt["gplan"], vt["g_end"])
            hot = side == "cerebras"
            ffon = (not hot) and vt["ff"]
            film_end = int(vt["film"](end)) if not hot else end
            toks = ";".join("%d,%d" % (m_["s0"], m_["tok"]) for m_ in plan if m_["tok"])
            total = sum(m_["tok"] for m_ in plan)
            r2 = v.get("gpu_tps_range")
            rng = f'<span style="font-family:var(--font-mono);font-size:12px;letter-spacing:.04em;text-transform:uppercase">range {int(r2[0])} to {int(r2[1])} across providers</span>' if (r2 and not hot) else ""
            title_c = "var(--accent)" if hot else "var(--ink)"
            pill_bg = "var(--accent)" if hot else "var(--pill-dark)"
            head = (f'<div style="position:absolute;left:24px;top:16px;right:24px;display:flex;align-items:center;gap:12px"><div><div class="ag-appname" style="color:{title_c};font-size:26px;font-weight:600;line-height:30px">{esc(label)}</div>'
                    f'<div style="font-family:var(--font-mono);font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3);line-height:16px">{esc(cfg["model"])}</div></div><span style="flex:1"></span>'
                    f'<span class="ag-chip" style="height:34px;padding:0 16px;border-radius:17px;background:{pill_bg};color:var(--on-accent);font-size:16px"><b data-clock data-from="{FIRST_MS}" data-stop="{end}" style="font-weight:600">0s</b></span></div>'
                    f'<div style="position:absolute;left:24px;top:68px;right:24px;display:flex;align-items:center;gap:22px;color:var(--ink-3);font-size:15px">'
                    f'<span><b data-tokens="{toks}" data-tps="{tps}" style="color:var(--ink);font-weight:600">0</b> tokens</span>'
                    f'<span class="ag-chip">{num(str(int(tps)), 300, 700)}<span style="margin-left:5px">tokens/s</span></span>{rng}</div>')
            rows = thread_rows(plan, avatar=None if hot else GENERIC_AVATAR, attach=attach_card(cfg, 260))   # HARD RULE: the Cerebras mark is on the Cerebras lane only
            view = (f'<div style="position:absolute;left:24px;top:108px;width:{PW - 48}px;height:{VIEW}px;overflow:hidden"><div class="thread-in" data-view="{VIEW}" data-lane="{side}" data-tps="{tps}" data-total="{total}" data-end="{end}" data-film-end="{film_end}" style="position:relative">{rows}</div></div>')
            # the follow-up composer of the source's lanes: its model chip reads ANALYZING while the lane works and READY once it is done
            comp = (f'<div style="position:absolute;left:24px;right:24px;top:{108 + VIEW + 16}px;height:92px;border-radius:18px;border:1px solid var(--line);background:var(--card)">'
                    f'<div style="padding:15px 18px;font-size:16px;color:var(--ink-3)">Ask a follow-up</div>'
                    f'<div style="position:absolute;left:14px;right:12px;bottom:10px;display:flex;align-items:center;gap:10px"><span style="color:var(--ink-2)">{A.ic("plus", 18, 1.6)}</span><span style="flex:1"></span>'
                    f'<span class="ag-chip" style="height:26px;padding:0 10px;font-size:12px;gap:8px;font-weight:500">{esc(cfg["model"])}<span data-state data-at="{film_end}" data-a="ANALYZING" data-b="READY" style="font-family:var(--font-mono);font-size:9.5px;letter-spacing:.07em;font-weight:600">ANALYZING</span></span>'
                    f'<span class="ag-send off" style="width:30px;height:30px">{A.ic("up", 15, 2.2)}</span></div></div>')
            word_c, pill_c = ("var(--accent)", "var(--accent)") if hot else ("#6c6c6a", "#5a5a58")
            done_bg = "#FBD9D5" if hot else "#D8D8D5"
            done = (f'<div class="versus-done" data-at="{film_end}" style="position:absolute;left:{(PW - 340) // 2}px;top:300px;width:340px;height:174px;border-radius:14px;background:{done_bg};box-shadow:0 20px 50px rgba(20,20,30,.16);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:9px;z-index:5;visibility:hidden">'
                    f'<div style="font-size:58px;font-weight:800;letter-spacing:-.02em;line-height:1;color:{word_c}">DONE</div>'
                    f'<span style="font-family:var(--font-mono);font-weight:700;font-size:26px;line-height:28px;color:#fff;background:{pill_c};border-radius:999px;padding:9px 16px;letter-spacing:.01em">{(end - FIRST_MS) / 1000:.2f} sec</span></div>')
            conf = f'<div class="versus-conf" data-at="{film_end}" data-cx="{PW // 2}" data-cy="{300 + 87}"></div>' if hot else ""
            ff = ""
            if ffon:   # the source's fast-forward badge: a translucent accent pill on the slow lane from FF_LEAD_MS after the fast lane is done until just before the slow lane is
                ff = (f'<div class="versus-ff" data-from="{vt["ff_at"]}" data-to="{max(vt["ff_at"] + 400, film_end - 350)}" style="position:absolute;left:{(PW - 240) // 2}px;top:330px;width:240px;height:136px;border-radius:48px;background:rgba(241,90,41,.92);color:#fff;display:none;align-items:center;justify-content:center;gap:20px;z-index:5;font-size:74px;font-weight:700;letter-spacing:-.02em">'
                      f'<svg viewBox="0 0 54 40" width="70" height="52"><path d="M2 3l22 17L2 37zM28 3l22 17-22 17z" fill="#fff"/></svg><span>{int(vt["ff"])}X</span></div>')
            ffa = f' data-ff-at="{vt["ff_at"]}" data-ff="{vt["ff"]}"' if ffon else ""
            inner = f'{head}{view}{comp}{done}{conf}' if hot else f'<div class="versus-grey" style="position:absolute;left:0;top:0;width:100%;height:100%">{head}{view}{comp}{done}{conf}</div>'
            out += f'<div class="versus-lane" data-lane-box="{side}"{ffa} style="position:absolute;left:{x}px;top:{TOP}px;width:{PW}px;height:{PH}px;border-radius:20px;background:var(--card-2);border:1px solid var(--line)">{inner}{ff}</div>'
        note = f'<div style="position:absolute;left:0;right:0;top:{TOP + PH + 22}px;text-align:center;color:var(--ink-3);font-size:14px">{esc(v["note"])}</div>'
        return window(out + note, timer=True)
    if kind == "intro":
        q = sc["intro"]; it = intro_times(q)
        logo = f'<div data-appear="120" style="margin-bottom:40px">{logo_html(q["logo"], 86)}</div>' if q.get("logo") else ""
        title = reveal([(q["title"], False)], it["title"][0], it["title"][1], tag="div", style="font-size:112px;line-height:1.1;letter-spacing:-.045em;font-weight:500;color:var(--ink);max-width:1500px")
        desc = '<div class="ag-claim-f" style="position:static;margin-top:44px;font-size:42px;line-height:1.38;letter-spacing:-.01em;max-width:1240px">' + reveal([(q["description"], False)], it["description"][0], it["description"][1], tag="div") + '</div>'
        pl = partner_html(cfg, 56) if it["lockup"] else ""
        lock = (f'<div data-appear="{it["lockup"]}" style="margin-top:70px;display:flex;align-items:center;justify-content:center;gap:34px">{A.logo(66)}'
                + (f'<span style="font-size:44px;font-weight:300;color:var(--ink);opacity:.7;line-height:1">×</span>{pl}' if pl else "") + '</div>') if it["lockup"] else ""
        body = f'<div style="position:absolute;left:0;top:0;width:1920px;height:1080px;display:flex;flex-direction:column;align-items:center;text-align:center;padding-top:260px;box-sizing:border-box">{logo}{title}{desc}{lock}</div>'
        return Pg.place(0, 0, f'<div style="position:relative;width:1920px;height:1080px">{body}</div>')
    if kind == "ask":
        q = sc["ask"]; t0, t1, t2 = ask_times(q); cx = chat_x(cfg)
        opts = "".join(f'<span data-appear="{t1 + 250 * (j + 1)}" style="display:inline-flex;align-items:center;height:34px;padding:0 16px;border-radius:17px;border:1px solid var(--line);background:var(--card);font-size:15px;color:var(--ink);margin:0 8px 8px 0">{esc(o)}</span>' for j, o in enumerate(q.get("options") or []))
        rows = (f'<div style="display:flex;flex-direction:column;align-items:flex-end;margin:0 0 18px"><div class="ag-bubble" style="position:static;width:auto;max-width:600px;padding:18px 20px;font-size:16.5px;line-height:24px;border-radius:20px;text-align:left">{esc(cfg["prompt"])}</div>{ATTACH[0]}</div>'
                f'<div style="display:flex;align-items:center;gap:10px;margin:0 0 12px;color:var(--ink-3);font-size:13.5px;border-bottom:1px solid var(--line);padding-bottom:10px">{A.mark(24)}<span>Worked for {cfg["answer"]["footer_seconds"]} seconds</span>{A.ic("fwd", 13, 2)}</div>'
                f'<div data-appear="{t0}" style="margin:0 0 18px"><div class="ag-order" style="position:static;padding:16px 20px 12px;font-size:16.5px;line-height:24px;background:var(--card-3)">'
                + reveal([(q["question"], False)], t0, t1 - t0, tag="div", style="margin:0 0 12px") + f'<div>{opts}</div></div></div>'
                f'<div data-appear="{t2}" style="display:flex;justify-content:flex-end;margin:0 0 18px"><div class="ag-bubble" style="position:static;width:auto;padding:12px 18px;font-size:16.5px;border-radius:20px">{esc(q["reply"])}</div></div>'
                + status_row(t2 + 250, sc["ms"] - cfg["fade_ms"]))
        view = f'<div style="position:absolute;left:{cx}px;top:96px;width:860px;height:740px;overflow:hidden"><div class="thread-in" data-view="740" style="position:relative">{rows}</div></div>'
        return window(view + docked("stop"), timer=True)
    if kind == "second-turn":
        q = sc["second"]; cx = chat_x(cfg); click = sc["click_at"]
        rows = prior_rows(cfg) + (f'<div data-appear="{click + 150}" style="display:flex;justify-content:flex-end;margin:0 0 18px"><div class="ag-bubble" style="position:static;width:auto;max-width:600px;padding:18px 20px;font-size:16.5px;line-height:24px;border-radius:20px;text-align:left">{esc(q["prompt"])}</div></div>' + status_row(click + 450, sc["ms"] - cfg["fade_ms"]))
        view = f'<div style="position:absolute;left:{cx}px;top:96px;width:860px;height:700px;overflow:hidden"><div class="thread-in" data-view="700" style="position:relative">{rows}</div></div>'
        x, y, w = 372, 868, 860
        sx, sy = x + w - 11 - 36, y - 44 + 112 - 10 - 36
        comp = (f'<div class="ag-composer" style="left:{x}px;top:{y - 44}px;width:{w}px;height:112px;border-radius:20px;box-shadow:none;border:1px solid var(--line);background:var(--card-2)">'
                f'<div class="ag-text" style="padding:16px 16px;font-size:19px;line-height:26px"><span data-type="{esc(q["prompt"])}" data-type-ms="{q["type_ms"]}"></span><span class="ag-caret" data-caret-until="{click}"></span></div>'
                f'<div class="ag-bar" style="left:16px;right:11px;bottom:10px;height:36px;gap:16px"><span style="color:var(--ink-2)">{A.ic("plus", 22, 1.6)}</span><span style="flex:1"></span>{A.model_pill(16, False, "var(--ink-2)", cfg["model"])}'
                f'<span class="ag-send off" data-send data-press="{click}" style="width:36px;height:36px">{A.ic("up", 18, 2.2)}</span></div></div>')
        mt = MEASURED.get("second-turn:%d" % sc["i"])
        tx, ty = (mt["tx"], mt["ty"]) if mt else (sx + 36 * .78, sy + 36 * .62)
        ptr = pointer_html(sc["pointer_from"], POINTER_MS, click, tx + 90, ty + 220, tx, ty)
        return window(view + comp + ptr, timer=True)
    if kind == "integration":
        q = sc["integration"]; it = integration_times(q); cx = chat_x(cfg)
        ctx = f'<div style="position:absolute;left:{cx}px;top:96px;width:860px;height:700px;overflow:hidden"><div style="position:relative">{prior_rows(cfg)}</div></div>' + docked("done")
        blurred = f'<div data-blur data-blur-from="0" data-blur-ms="700" data-blur-px="14" style="position:absolute;left:0;top:0;width:100%;height:100%">{ctx}</div>'
        head = (f'<div style="display:flex;align-items:center;gap:10px;padding:16px 26px;border-bottom:1px solid var(--line);color:var(--ink-3);font-size:14px"><span style="font-family:var(--font-mono);font-size:12px;letter-spacing:.06em;text-transform:uppercase">{esc(q.get("tag", ""))}</span></div>')
        title = reveal([(q["title"], True)], it["title"][0], it["title"][1], tag="div", style="font-size:26px;line-height:34px;letter-spacing:-.01em")
        badge = f'<span data-appear="{it["badge"]}" class="ag-chip" style="height:26px">{esc(q["badge"])}</span>' if it["badge"] else ""
        chips = "".join(f'<span data-appear="{t}" style="display:inline-flex;align-items:center;height:26px;padding:0 12px;border-radius:13px;border:1px solid var(--line);font-family:var(--font-mono);font-size:12px;color:var(--ink-2)">{esc(c)}</span>' for t, c in zip(it["chips"], q.get("chips") or []))
        body = "".join(f'<div data-appear="{t}" style="margin-top:12px;font-size:16.5px;line-height:25px;color:var(--ink-2)">{reveal([(ln, False)], t, d, tag="span")}</div>' for (t, d), ln in zip(it["body"], q.get("body") or []))
        card = (f'<div data-appear="900" style="position:absolute;left:330px;top:140px;width:948px;border-radius:22px;background:var(--card);box-shadow:0 30px 80px rgba(20,20,30,.28);overflow:hidden;z-index:4">{head}'
                f'<div style="padding:22px 26px 28px">{title}<div style="display:flex;gap:10px;align-items:center;margin-top:12px;flex-wrap:wrap">{badge}{chips}</div>{body}</div></div>')
        return window(blurred + card, timer=False)
    if kind == "browse":
        q = sc["browse"]; pages = q["pages"]; n = len(pages)
        T0 = 1100; dflt = (sc["ms"] - T0 - 600) / n
        t = T0; times = []
        for pg in pages:
            d = int(pg.get("ms", dflt)); times.append((t, t + d)); t += d
        host = lambda u: re.sub(r"^https?://", "", u).split("/")[0]
        PX, PY, PWD, PHT = 560, 96, 1010, 870
        tabs = "".join(f'<div data-appear="{a0}" style="display:flex;align-items:center;gap:8px;height:34px;padding:0 12px;border-radius:9px 9px 0 0;background:{"var(--card)" if True else ""};border:1px solid var(--line);border-bottom:0;font-size:13px;color:var(--ink-2);max-width:210px"><span style="color:var(--ink-3)">{A.ic("globe", 14, 1.7)}</span><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{esc(pg.get("title") or pg["heading"])}</span><span style="color:var(--ink-3)">{A.ic("close", 12, 2)}</span></div>' for (a0, _), pg in zip(times, pages))
        urls = "".join(f'<span data-show-from="{a0}" data-show-to="{a1}" style="position:absolute;left:14px;top:0;line-height:34px;font-size:14px;color:var(--ink-2)">{esc(pg["url"])}</span>' for (a0, a1), pg in zip(times, pages))
        nav = (f'<div style="display:flex;align-items:center;gap:14px;height:46px;padding:0 14px;border-bottom:1px solid var(--line);color:var(--ink-3)">{A.ic("back", 18, 1.8)}{A.ic("fwd", 18, 1.8)}{A.ic("reload", 18, 1.8)}'
               f'<div style="position:relative;flex:1;height:34px;border-radius:17px;background:var(--card-2);overflow:hidden">{urls}</div>{A.ic("ext", 18, 1.8)}{A.ic("dl", 18, 1.8)}{A.ic("edit", 18, 1.8)}</div>')
        pagehtml = ""
        for j, ((a0, a1), pg) in enumerate(zip(times, pages)):
            lines = pg.get("lines") or []
            by = 170 + 30 * len(lines) + 24
            ck = int(a0 + (a1 - a0) * 0.7)
            btn = f'<div data-send data-press="{ck}" style="margin-top:24px;width:230px;height:50px;border-radius:25px;background:var(--accent);color:var(--on-accent);display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:600">{esc(pg["button"])}</div>' if pg.get("button") else ""
            ptr = ""
            if pg.get("pointer") and pg.get("button"):
                mt = MEASURED.get("browse:%d:%d" % (sc["i"], int(a0)))
                tx, ty = (mt["tx"], mt["ty"]) if mt else (40 + 230 * .78, 170 + 30 * len(lines) + 24 + 50 * .62)
                ptr = pointer_html(ck - POINTER_MS, POINTER_MS, ck, tx + 300, ty + 400, tx, ty)
            mod = ""
            if pg.get("modal"):
                mt = int(a0 + (a1 - a0) * 0.7) + 300 if pg.get("pointer") else int(a0 + (a1 - a0) * 0.55)
                mb = "".join(f'<span style="display:inline-flex;align-items:center;height:42px;padding:0 20px;border-radius:21px;{"background:var(--accent);color:var(--on-accent)" if m_ == 0 else "border:1px solid var(--line)"};font-size:15px;font-weight:600;margin-right:10px">{esc(b)}</span>' for m_, b in enumerate(pg["modal"].get("buttons") or []))
                mod = (f'<div data-show-from="{mt}" data-show-to="{a1}" style="position:absolute;left:0;top:0;width:100%;height:100%;background:rgba(0,0,0,.34);z-index:3"><div style="position:absolute;left:230px;top:200px;width:520px;padding:26px 28px;border-radius:18px;background:var(--card);box-shadow:0 24px 60px rgba(0,0,0,.3)">'
                       f'<div style="font-size:22px;font-weight:600;margin-bottom:16px">{esc(pg["modal"]["title"])}</div><div>{mb}</div></div></div>')
            ls = "".join(f'<div style="font-size:16px;line-height:30px;color:var(--ink-2)">{esc(l)}</div>' for l in lines)
            sc_px = int(pg.get("scroll", 0))
            inner = (f'<div class="bpage-in" data-scroll-from="{a0}" data-scroll-to="{a1}" data-scroll="{sc_px}" style="position:relative;padding:0 40px"><div style="display:flex;align-items:center;height:56px;margin:0 -40px;padding:0 40px;border-bottom:1px solid var(--line);font-family:var(--font-mono);font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3)">{esc(host(pg["url"]))}</div>'
                     f'<div style="margin-top:36px;font-size:34px;line-height:42px;font-weight:600;letter-spacing:-.02em">{esc(pg["heading"])}</div><div style="margin-top:18px">{ls}</div>' + "".join(f'<div style="height:120px;margin-top:22px;border-radius:12px;background:var(--card-2)"></div>' for _ in range(((780 + sc_px - 380) // 142 + 2) if sc_px else 0)) + '</div>')
            inner = inner[:-6] + btn + "</div>"
            pagehtml += f'<div data-show-from="{a0}" data-show-to="{a1}" style="position:absolute;left:0;top:0;width:100%;height:100%;overflow:hidden">{inner}{ptr}{mod}</div>'
        pane = (f'<div data-grow data-from="300" data-ms="700" style="position:absolute;left:{PX}px;top:{PY}px;width:{PWD}px;height:{PHT}px;border-radius:14px;border:1px solid var(--line);background:var(--card);overflow:hidden">'
                f'<div style="display:flex;align-items:flex-end;gap:6px;height:44px;padding:8px 10px 0;background:var(--card-2)">{tabs}<span style="flex:1"></span><span style="color:var(--ink-3);padding-bottom:8px">{A.ic("expand", 18, 1.7)}</span></div>{nav}'
                f'<div style="position:relative;height:{PHT - 90}px">{pagehtml}</div></div>')
        thumbs = "".join(f'<div data-show-from="{a0}" data-show-to="{a1}" style="position:absolute;left:0;top:0;width:100%;height:100%;padding:12px;box-sizing:border-box"><div style="font-size:10px;font-family:var(--font-mono);color:var(--ink-3);text-transform:uppercase">{esc(host(pg["url"]))}</div><div style="margin-top:6px;font-size:14px;font-weight:600;line-height:17px">{esc(pg["heading"])}</div><div style="margin-top:8px;height:5px;width:70%;background:var(--line);border-radius:3px"></div><div style="margin-top:5px;height:5px;width:52%;background:var(--line);border-radius:3px"></div></div>' for (a0, a1), pg in zip(times, pages))
        m = cfg["meter"]
        chat = (f'<div data-lerp data-left0="372" data-left1="36" data-w0="860" data-w1="480" data-from="300" data-ms="700" style="position:absolute;left:372px;top:96px;width:860px">'
                f'<div style="display:flex;justify-content:flex-end;margin-bottom:22px"><div class="ag-bubble" style="position:static;width:auto;max-width:460px;padding:16px 18px;font-size:15.5px;line-height:23px;border-radius:20px;text-align:left">{esc(cfg["prompt"])}</div></div>'
                f'<div style="display:flex;align-items:center;gap:8px;color:var(--ink-2);font-size:14.5px;margin-bottom:10px">{A.mark(24)}<span>{esc(cfg["tool"]["name"])}</span>{A.ic("fwd", 13, 2)}</div>'
                f'<div style="position:relative;width:300px;height:170px;border-radius:12px;background:var(--card);border:1px solid var(--line);overflow:hidden">{thumbs}</div>'
                f'<div style="display:flex;align-items:center;gap:8px;margin-top:12px;color:var(--ink-3);font-size:12.5px"><span>{num(m["seconds"], 600, 2400)}s · {num(m["tokens"], 600, 2400)} output tokens ·</span><span class="ag-chip" style="height:22px;font-size:11px;padding:0 9px">{num(m["rate"], 600, 2400)}</span></div></div>')
        dk = docked("stop")
        dk = dk[:dk.index('<span style="position:absolute;left:')].replace('<div class="ag-composer" style="', '<div class="ag-composer" data-lerp data-left0="372" data-left1="36" data-w0="860" data-w1="480" data-from="300" data-ms="700" style="', 1)   # the composer docks into the narrowing chat column
        return window(chat + pane + dk, timer=True)
    if kind in ("turn", "answer"):
        cx = chat_x(cfg)
        status = (f'<div class="ag-status" style="left:{cx}px;top:238px"><span class="ag-spin" style="display:block;color:var(--ink-3)">{A.ic("ring", 22, 2)}</span><span style="margin-left:6px">Preparing this turn... <span data-elapsed>1s</span></span></div>')
        tool = (f'<span style="position:absolute;left:{cx - 50}px;top:{300 - 14}px">{A.mark(28)}</span><div class="ag-toolhead" style="left:{cx + 4}px;top:{300 - 13}px">{A.ic("browser", 19, 1.8)}'
                f'<span style="margin-left:4px">{esc(cfg["tool"]["name"])}</span>{A.ic("fwd", 14, 2)}</div>'
                f'<div class="ag-meter" style="left:{cx}px;top:352px"><span style="display:block">{A.mark(24)}</span><span>{num(m["seconds"])}s · {num(m["tokens"])} output tokens ·</span><span class="ag-chip">{num(m["rate"])}</span></div>')
        body = bubble(cfg["prompt"], right=376)
        if kind == "turn":
            return window(body + status + tool + docked("stop"), timer=True)
        a = cfg["answer"]
        st = int(a.get("stream_ms", 0))
        chunks = [[(a["lead"], False)]] + [([(b[0], True), (" " + b[1], False)] if isinstance(b, list) else [(b, False)]) for b in a["bullets"]]
        total_w = sum(len(split_words(t)) for ch in chunks for t, _ in ch) or 1
        starts = []
        def chunk_html(ch, tag="span", style=""):
            n = sum(len(split_words(t)) for t, _ in ch)
            d0 = 500 + int(st * nonlocal_t[1] / total_w); nonlocal_t[1] += n
            starts.append(d0)
            if not st:
                return "".join(("<b>%s</b>" if b else "%s") % esc(t) for t, b in ch)
            return reveal(ch, d0, max(1, int(st * n / total_w)), tag, style)
        nonlocal_t = [0, 0]
        lead_html = chunk_html(chunks[0])
        # PROGRESSIVE: the card exists from the first word of the lead, each bullet (its marker too) from ITS first word, the footer when the text is done: nothing is drawn empty and waiting for its text
        ap = (lambda ms: f' data-appear="{ms}"') if st else (lambda ms: "")
        inner_b = [chunk_html(ch) for ch in chunks[1:]]   # (called in order, so `starts` is complete)
        bullets = "".join(f'<li{ap(starts[1 + j])} style="margin-top:6px">{h}</li>' for j, h in enumerate(inner_b))
        done_at = 500 + st + 200
        dd = done_at + 100 if st else 450
        card = (f'<div style="position:absolute;left:{cx}px;top:350px;width:860px"><div class="ag-order"{ap(500)} style="position:static;padding:16px 20px 18px;font-size:16.5px;line-height:24px;background:var(--card-3)">{lead_html}'
                f'{("<ul" + ap(starts[1]) + " style=margin-top:10px>" + bullets + "</ul>") if bullets else ""}</div>'
                f'<div class="ag-foot"{ap(done_at)} style="position:static;margin-top:16px;font-size:13.5px">Done in {num(a["footer_seconds"], dd)} seconds &nbsp;·&nbsp; {num(a["footer_tokens"], dd)} output tokens</div>'
                f'<div class="ag-foot"{ap(done_at)} style="position:static;margin-top:6px;font-size:13.5px;display:flex;align-items:center">Assistant<span class="ag-chip" style="height:24px;margin:0 8px;font-size:14px;padding:0 9px">{num(m["rate"], dd)} · TTFT {num(m["ttft"], dd)}</span><span>just now</span></div></div>')
        worked = f'<span style="position:absolute;left:{cx - 50}px;top:{300 - 14}px">{A.mark(28)}</span><div class="ag-worked" style="left:{cx + 4}px;top:{300 - 10}px;width:856px">Worked for {num(a["footer_seconds"])} seconds {A.ic("fwd", 13, 2)}</div>'
        foot = ""
        if a.get("confetti"):
            foot = f'<div class="versus-conf" data-at="{done_at - 200 if st else 600}" data-cx="{cx + 430}" data-cy="520"></div>'
        return window(body + worked + card + foot + docked("done"), timer=True)
    if kind == "claim":
        c = cfg["claim"]
        return Pg.place(0, 0, f'''<div style="position:relative;width:1920px;height:1080px"><div class="ag-claim-h" style="top:410px;font-weight:500">{esc(cfg["model"])}</div>
<div class="ag-claim-l" style="top:572px;font-size:51px;letter-spacing:-.03em">Up to <span class="ag-n" style="font-weight:500" data-count="{int(c["number"])}">{int(c["number"]):,}</span> {esc(c["unit"])}<sup>*</sup></div>
<div class="ag-claim-f" style="top:1002px;font-size:22px">{esc(c["footnote"])}</div></div>''')
    if kind == "ground":
        return Pg.place(0, 0, '<div style="position:relative;width:1920px;height:1080px"></div>')
    if kind == "lockup":
        if sc.get("variant") == "powered-by":   # reference video 2: "powered by" in a light face, then the house logo
            return Pg.place(400, 400, f'<div style="position:relative;width:1120px;height:280px"><div class="ag-lockup" style="top:49px;height:182px;gap:44px"><span style="font-size:58px;font-weight:300;letter-spacing:-.02em;color:var(--ink)">powered by</span>{A.logo(182)}</div></div>')
        partner = partner_html(cfg, 104)
        tail = ('<span class="ag-hair"></span>' + partner) if partner else ""
        return Pg.place(400, 400, f'<div style="position:relative;width:1120px;height:280px"><div class="ag-lockup" style="top:49px;height:182px">{A.logo(182)}{tail}</div></div>')
    raise Refusal(kind)


def partner_svg(cfg):
    kimi = os.path.join(ROOT, "kits", "kimi", "brand", "kimi_logo.svg")   # Kimi by default; a checkout without that kit falls back to the neutral stand-in
    p = cfg.get("partner_logo") or (kimi if os.path.exists(kimi) else "templates/agent-film/partner-logo.svg")
    return build.inline_file(ROOT, p)


cfg_model = [""]


def build_page(cfg, outdir, cloud=False):
    cfg_model[0] = cfg["model"]
    ATTACH[0] = attach_card(cfg)
    TIMER[0] = None
    if cfg.get("timer"):
        runs = [x for x in cfg["scenes"] if x["scene"] in ("turn", "thread", "versus", "answer")]
        if runs:
            f0 = runs[0]["start"]
            ans = [x for x in runs if x["scene"] == "answer"]
            TIMER[0] = (f0, ans[0]["start"] if ans else runs[-1]["start"] + runs[-1]["ms"])
    theme = cfg["theme"]
    layers = []
    for i, sc in enumerate(cfg["scenes"]):
        kind = sc["scene"]
        pk = "claim" if kind in ("claim", "ground", "intro") else "lockup" if kind == "lockup" else ("typing" if kind == "typing" else None)
        html = Pg.page(theme, lambda t, sc=sc: scene_html(cfg, sc, t), pk)
        if cfg.get("words"):
            html = localize(html, cfg["words"])
        morph = ' data-morph="1"' if i > 0 and cfg["scenes"][i - 1]["scene"] == "typing" and kind in ("welcome", "turn", "answer", "thread", "versus", "popin") else ""
        cut = ' data-cut="1"' if sc.get("cut") else ""
        layers.append(f'<div class="scene" data-i="{i}" data-start="{sc["start"]}" data-ms="{sc["ms"]}" data-kind="{kind}"{morph}{cut} style="opacity:0">{html}</div>')
    css = build.fontface() + A.CSS + """
html,body{margin:0;background:#000;width:1920px;height:1080px;overflow:hidden}
.ag{overflow-wrap:anywhere}   /* a long unbroken word (a URL, a hash, a pasted token) wraps instead of running out of its box */
.scene{position:absolute;left:0;top:0;width:1920px;height:1080px}
.versus-grey{filter:grayscale(1)}   /* the competitor lane is DESATURATED, as the comparison video's losing lane is: the whole lane (marks, chips, bubble, accent) loses its colour whatever the theme's own colours are; the fast-forward badge sits outside it */
.rv-off{display:none!important}   /* PROGRESSIVE: a component that has not begun, and a word not yet rendered, take NO room (film.js toggles this class from the time): boxes grow with their text, as an LLM-rendered component does */
.versus-conf{position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none;z-index:6}
.versus-conf i{position:absolute;display:block;border-radius:1px}
"""
    engine = open(os.path.join(ROOT, "components", "agent", "film.js"), encoding="utf-8").read()
    popin = ""
    if _popin(cfg):
        if cloud:   # the cloud page is ONE self-contained file (the function is handed only the page): the clip's frames ride inside it, at a lower rate and quality so it stays under the invoke limit
            import base64
            d = os.path.join(outdir, "popin-cloud")
            names = sorted(os.listdir(d))
            data = ["data:image/jpeg;base64," + base64.b64encode(open(os.path.join(d, n), "rb").read()).decode() for n in names]
            popin = '<script>window.AGENT_POPIN=%s</script>' % json.dumps({"data": data, "fps": CLOUD_POPIN_FPS, "frames": len(data), "speed": cfg["popin"].get("speed", 1), "base": cfg["popin"].get("base", 0)})
        else:
            popin = '<script>window.AGENT_POPIN=%s</script>' % json.dumps({"dir": "popin/", "fps": cfg["fps"], "frames": cfg["popin"].get("frames", 0), "speed": cfg["popin"].get("speed", 1), "base": cfg["popin"].get("base", 0)})
    return (f'<!doctype html><meta charset=utf-8><title>{esc(cfg["slug"])}</title><style>{css}</style>{"".join(layers)}'
            f'<script>{A.BLOOM_JS}</script><script>{A.GROUND_JS}</script>{popin}<script>window.AGENT_FILM={json.dumps({"duration": cfg["duration"], "fade": cfg["fade_ms"], "fps": cfg["fps"]})}</script><script>{engine}</script>')


MAX_CLIP_MS = 120000   # the longest stretch of a clip a film may use (frames are extracted for it; a 10-minute recording is trimmed with clip_from and ms, never extracted whole)


def clip_info(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        w, h = [int(x) for x in r.stdout.strip().split(",")[:2]]
    except ValueError:
        refuse("popin video %s is not a video ffmpeg can read" % path)
    return w, h


def popin_fit(cfg):
    """cover (fill the 16:9 window, cropping) only for a clip that is already 16:9 within 3%; any other shape (a 16:10 laptop recording, a phone's 9:16, a 4:3 screen) is CONTAINED, whole, with black bars: never cut off the user's interface"""
    f = (cfg["popin"].get("fit") or "auto")
    if f not in ("auto", "cover", "contain"):
        refuse("popin.fit is auto, cover or contain, not %r" % f)
    if f != "auto":
        return f
    w, h = clip_info(cfg["popin"]["video"])
    return "cover" if abs((w / h) / (16 / 9) - 1) <= 0.03 else "contain"


def popin_window(cfg):
    """the stretch of the clip the popin scenes actually show, in clip milliseconds: from the earliest clip_from to the latest end"""
    sp = float(cfg["popin"].get("speed", 1))
    ranges = [(float(x.get("clip_from", 0)) * sp, (float(x.get("clip_from", 0)) + float(x["ms"])) * sp) for x in cfg["scenes"] if x["scene"] == "popin"]
    start, end = min(r[0] for r in ranges), max(r[1] for r in ranges)
    if end - start > MAX_CLIP_MS:
        refuse("the pop-in scenes use %.0f s of the clip; at most %d s. Use clip_from and ms to take the part you want, or cut the video first" % ((end - start) / 1000, MAX_CLIP_MS // 1000))
    return start, end


def extract_popin(cfg, outdir):
    v = cfg["popin"]["video"]
    fit = popin_fit(cfg); cfg["popin"]["fit"] = fit
    start, end = popin_window(cfg)
    cfg["popin"]["base"] = int(start)
    def vf(w, h, fps):
        scale = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d" % (w, h, w, h)) if fit == "cover" else ("scale=%d:%d:force_original_aspect_ratio=decrease:force_divisible_by=2,pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=black" % (w, h, w, h))
        return "fps=%d,%s" % (fps, scale)
    win = ["-ss", "%.3f" % (start / 1000), "-t", "%.3f" % ((end - start) / 1000 + 0.5)]
    d = os.path.join(outdir, "popin"); os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + win + ["-i", v, "-vf", vf(1608, 905, cfg["fps"]), "-q:v", "3", os.path.join(d, "%05d.jpg")], check=True)
    cfg["popin"]["frames"] = len(os.listdir(d))
    dc = os.path.join(outdir, "popin-cloud"); os.makedirs(dc, exist_ok=True)
    for f in os.listdir(dc):
        os.remove(os.path.join(dc, f))
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + win + ["-i", v, "-vf", vf(1280, 720, CLOUD_POPIN_FPS), "-q:v", "7", os.path.join(dc, "%05d.jpg")], check=True)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cfg = load(sys.argv[1])
    outdir = os.path.join(ROOT, "out", "agent-film", cfg["slug"])
    os.makedirs(outdir, exist_ok=True)
    if _popin(cfg):
        extract_popin(cfg, outdir)
    p = os.path.join(outdir, "film.html")

    def write_and_measure():
        open(p, "w", encoding="utf-8").write(build_page(cfg, outdir))
        r = subprocess.run(["node", os.path.join(ROOT, "tools", "agent-film-measure.mjs"), p], capture_output=True, text=True)
        if r.returncode:
            raise Refusal("the measure pass failed: " + (r.stderr or r.stdout)[-400:])
        return json.loads(r.stdout)
    MEASURED.clear()
    m2 = write_and_measure()      # pass 1: the designed numbers; what Chrome measures there
    settled = False
    for _ in range(4):            # build with what was measured and measure again, until two passes agree: a composer that grows for a long prompt moves the click target, which the next pass then measures
        m1 = m2
        MEASURED.update(m1)
        m2 = write_and_measure()
        if all(abs(vv - m1[k][kk]) <= 0.6 for k, v in m2.items() for kk, vv in v.items()):
            settled = True
            break
    if not settled:
        refuse("the layout did not settle after 4 passes (the text is too long or too awkward for the layout): shorten it")
    for k, v in m2.items():
        if k.startswith("answer:") and v["bottom"] > v["comp_top"] - 8:
            refuse("scene %s: the answer card ends at y=%d, %d px into the docked composer (it starts at y=%d): shorten the answer or split it across scenes" % (k.split(":")[1], v["bottom"], v["bottom"] - v["comp_top"] + 8, v["comp_top"]))
        if k.startswith("intro:") and v["bottom"] > 1010:
            refuse("scene %s: the intro text runs to y=%d of 1080 (it must end by 1010): shorten the title or the description" % (k.split(":")[1], v["bottom"]))
        if k.startswith("claim:") and (v["width"] > 1840 or v["bottom"] > 1040):
            refuse("scene %s: the model name or the claim line is too wide or too tall for the slide (%d px wide, to y=%d): shorten `model`, `claim.unit` or `claim.footnote`" % (k.split(":")[1], v["width"], v["bottom"]))
        if k.startswith("typing:") and v["text_h"] + 74 > 430:
            refuse("scene %s: the typed prompt is %d px tall, more than the composer can grow to (430 px incl. the bar): shorten the prompt" % (k.split(":")[1], v["text_h"]))
    cfg["measured"] = m2
    open(os.path.join(outdir, "film.cloud.html"), "w", encoding="utf-8").write(build_page(cfg, outdir, cloud=True))
    trans = [{"from": cfg["scenes"][i - 1]["scene"], "to": cfg["scenes"][i]["scene"], "how": "cut" if cfg["scenes"][i].get("cut") else "morph" if cfg["scenes"][i - 1]["scene"] in MORPH_FROM and cfg["scenes"][i]["scene"] in ("welcome", "turn", "answer", "thread", "versus", "popin") else "crossfade", "at": cfg["scenes"][i]["start"]} for i in range(1, len(cfg["scenes"]))]
    json.dump({"slug": cfg["slug"], "measured": cfg["measured"], "popin": _popin(cfg), "duration": cfg["duration"], "fps": cfg["fps"], "scenes": [{"scene": s["scene"], "start": s["start"], "ms": s["ms"]} for s in cfg["scenes"]], "transitions": trans}, open(os.path.join(outdir, "film.json"), "w"), indent=1)
    print(p, "%.1f s" % (cfg["duration"] / 1000))


if __name__ == "__main__":
    main()
