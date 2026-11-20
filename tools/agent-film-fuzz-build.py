#!/usr/bin/env python3
"""THE LAYOUT MUST NOT BREAK EITHER: awkward but VALID inputs (emoji, right-to-left and CJK text, a 400-letter word, texts at their maximum, 100 messages, a PNG logo, a phone's 9:16 recording, a three-minute 4:3 recording trimmed with clip_from) are built in a real Chrome; each must be built and measured, or refused with a reason; never a crash, never raw markup from the user's text.

    python3 tools/agent-film-fuzz-build.py [name ...]      (about 30 s a case)
Needs /tmp/fz/long43.mp4, vertical.mp4 and logo.png (the script makes them with ffmpeg if they are missing).
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
FZ = "/tmp/fz"; os.makedirs(FZ, exist_ok=True)
if not os.path.exists(FZ + "/long43.mp4"):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=640x480:rate=30", "-t", "180", "-pix_fmt", "yuv420p", FZ + "/long43.mp4"], check=True)
if not os.path.exists(FZ + "/vertical.mp4"):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=720x1280:rate=30", "-t", "12", "-pix_fmt", "yuv420p", FZ + "/vertical.mp4"], check=True)
if not os.path.exists(FZ + "/logo.png"):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x1e3cc8:s=400x120", "-frames:v", "1", FZ + "/logo.png"], check=True)


def sb(slug, scenes, **kw):
    return dict({"slug": slug, "model": "Kimi", "prompt": "Do the thing.", "theme": "paper", "claim": {"number": 1000, "unit": "tokens per second"}, "scenes": scenes}, **kw)


MSG = lambda t, who="Agent": {"who": who, "text": t}
UNI = "😀 Résumé naïve — 日本語のテキスト — مرحبا بالعالم — Ελληνικά"
CASES = {
    "unicode": sb("fz-unicode", [{"scene": "intro", "intro": {"title": "Ünïcode 日本語 😀", "description": UNI}}, {"scene": "typing"}, {"scene": "thread", "thread": [{"kind": "user", "text": UNI}, MSG(UNI, "Ägent 😀")]}, {"scene": "answer", "answer": {"lead": UNI, "bullets": [[UNI, UNI]]}}, {"scene": "claim"}, {"scene": "lockup"}], prompt=UNI),
    "longword": sb("fz-longword", [{"scene": "intro", "intro": {"title": "A" * 60, "description": "x" * 300}}, {"scene": "typing"}, {"scene": "thread", "thread": [{"kind": "user", "text": "u" * 380}, MSG("https://example.com/" + "a1b2" * 100)]}, {"scene": "answer", "answer": {"lead": "L" * 150, "bullets": [["B" * 60 + ":", "c" * 300]]}}, {"scene": "claim"}, {"scene": "lockup"}], prompt="p" * 390),
    "maxtext": sb("fz-maxtext", [{"scene": "intro", "intro": {"title": "T" * 100, "description": ("word " * 120)[:600]}}, {"scene": "typing"}, {"scene": "thread", "thread": [{"kind": "user", "text": "q"}, MSG(("sentence number one is here. " * 40)[:1200])]}, {"scene": "answer", "answer": {"lead": "Lead " * 30, "bullets": [("bullet text " * 33)[:400]] * 10}}, {"scene": "claim"}, {"scene": "lockup"}], prompt=("a long prompt " * 30)[:400]),
    "manymessages": sb("fz-many", [{"scene": "typing"}, {"scene": "thread", "thread": [{"kind": "user", "text": "go"}] + [MSG("Step %d: " % k + "did some work and found a result worth noting. " * 2, "Agent") for k in range(60)]}, {"scene": "claim"}, {"scene": "lockup"}]),
    "vertical": sb("fz-vertical", [{"scene": "intro", "intro": {"title": "Phone app", "description": "A phone recording, 9:16."}}, {"scene": "popin"}, {"scene": "claim"}, {"scene": "lockup"}], popin={"video": FZ + "/vertical.mp4"}),
    "longclip": sb("fz-longclip", [{"scene": "intro", "intro": {"title": "Long clip", "description": "A three minute 4:3 recording, trimmed to eight seconds from the one minute mark."}}, {"scene": "popin", "ms": 8000, "clip_from": 60000}, {"scene": "claim"}, {"scene": "lockup"}], popin={"video": FZ + "/long43.mp4"}),
    "longclip-untrimmed": sb("fz-untrimmed", [{"scene": "popin"}, {"scene": "claim"}, {"scene": "lockup"}], popin={"video": FZ + "/long43.mp4"}),
    "pnglogo": sb("fz-pnglogo", [{"scene": "intro", "intro": {"title": "With a logo", "description": "A PNG logo above the title.", "logo": FZ + "/logo.png"}}, {"scene": "claim"}, {"scene": "lockup"}]),
    "wideclaim": sb("fz-wideclaim", [{"scene": "claim"}, {"scene": "lockup"}], model="A Very Long Model Name Indeed Of Many Words Here", claim={"number": 1000, "unit": "tokens per second on a very large cluster of systems", "footnote": "*" + "f" * 150}),
    "html": sb("fz-html", [{"scene": "intro", "intro": {"title": "<script>alert(1)</script>", "description": "<img src=x onerror=alert(2)> &amp; \"quotes\""}}, {"scene": "claim"}, {"scene": "lockup"}]),
}


def main():
    names = sys.argv[1:] or list(CASES)
    bad = 0
    for n in names:
        c = CASES[n]
        p = os.path.join(FZ, n + ".json"); json.dump(c, open(p, "w"))
        r = subprocess.run([sys.executable, "artifact/agent_film.py", p], cwd=ROOT, capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip()
        page = os.path.join(ROOT, "out", "agent-film", c["slug"], "film.html")
        if r.returncode == 0:
            html = open(page, encoding="utf-8").read()
            raw = "<script>alert" in html or "<img src=x" in html
            print("BUILT  %-20s %s%s" % (n, out.splitlines()[-1].split("film.html")[-1].strip(), "   RAW MARKUP IN PAGE!" if raw else ""))
            bad += 1 if raw else 0
        elif "refused" in out or "NOT READY" in out:
            print("REFUSED %-19s %s" % (n, out.splitlines()[-1][:230]))
        else:
            print("CRASH  %-20s %s" % (n, out[-300:].replace("\n", " | "))); bad += 1
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
