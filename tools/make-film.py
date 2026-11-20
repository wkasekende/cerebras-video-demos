#!/usr/bin/env python3
"""MAKE A FILM IN ONE COMMAND: the guided path from your input to an MP4, with the rules built in so you cannot forget them.

    python3 tools/make-film.py --check                      (seconds) is this machine ready? python3, node, ffmpeg, ffprobe, puppeteer and a Chrome
    python3 tools/make-film.py <input.json> [--theme <a theme in THEMES, artifact/agent_film.py>] [--still [--at MS]] [--cloud] [--no-verify]

<input.json> is EITHER a storyboard (templates/project-demo/storyboard.json: you have a recording) OR a run log (templates/from-run/run.json: you have what your agent did as text;
it has a "messages" key). Steps, each of which stops the command with the reason if it fails:
  1. a run log is turned into a storyboard (tools/agent-film-from-run.py: every duration derived from your words)
  2. --theme replaces the storyboard's theme (the only way a look changes: colours and weights are not keys on purpose)
  3. the storyboard is checked against the closed schema and built (artifact/agent_film.py: it also MEASURES the layout in a real Chrome and refuses an answer that does not fit)
  4. about 600 deterministic checks run (tools/agent-film-verify.mjs): a film that does not say `0 failed` is NEVER rendered
  5. --still: ONE frame is photographed and its path printed (the fast loop: look at it before you render). By default it is the money shot: the moment both DONE cards are up in a
     side-by-side film, the pop-in clip a little way in, else the middle of the second scene; `--at MS` photographs any film time (the scene list printed before it gives every start). Otherwise the film is rendered to an MP4,
     locally, or with --cloud on the AWS function (clips and the glow, bloom and tile themes go in 16 windows: a busy window is larger than the function's 6 MB reply limit and a canvas ground is slow)
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "artifact")); sys.path.insert(0, HERE)
import agent_film as A  # noqa: E402
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("from_run", os.path.join(HERE, "agent-film-from-run.py"))
from_run = importlib.util.module_from_spec(spec); spec.loader.exec_module(from_run)


def run(cmd, what):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        sys.exit("STOPPED at %s:\n%s" % (what, (r.stdout + r.stderr).strip()[-1500:]))
    return r.stdout.strip()


def check():
    """is this machine ready? (seconds, not the minutes of agent-film-check.sh)"""
    bad = []
    if sys.version_info < (3, 8):
        bad.append("python3 3.8+ (this is %d.%d)" % sys.version_info[:2])
    for tool in ("node", "ffmpeg", "ffprobe"):
        r = subprocess.run([tool, "-version" if tool != "node" else "--version"], capture_output=True, text=True) if __import__("shutil").which(tool) else None
        if not r or r.returncode:
            bad.append("%s on your PATH" % tool)
    if not os.path.isdir(os.path.join(ROOT, "node_modules", "puppeteer")) and not os.path.isdir(os.path.join(ROOT, "node_modules", "puppeteer-core")):
        bad.append("`npm install` in this folder (puppeteer is missing)")
    else:
        r = subprocess.run(["node", "-e", "import('./tools/chrome.mjs').then(async m=>{const b=await m.launch();await b.close();console.log('chrome ok')}).catch(e=>{console.error(e.message);process.exit(1)})"], cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            bad.append("a working Chrome: " + (r.stderr or r.stdout).strip()[:200])
    if bad:
        sys.exit("NOT READY, you need:\n  - " + "\n  - ".join(bad))
    print("READY: python3, node, ffmpeg, ffprobe, puppeteer and Chrome all work. (Optional, for --cloud: the AWS CLI and credentials.)")


def main():
    args = sys.argv[1:]
    if args and args[0] == "--check":
        return check()
    if not args or args[0].startswith("-"):
        sys.exit(__doc__)
    src = args[0]
    theme = args[args.index("--theme") + 1] if "--theme" in args else None
    data = json.load(open(src, encoding="utf-8"))
    film = from_run.build(data) if "messages" in data else data
    if theme:
        if theme not in A.THEMES:
            sys.exit("STOPPED: theme %r is not one of %s" % (theme, A.THEMES))
        film["theme"] = theme
    pv = (film.get("popin") or {}).get("video")
    if pv and not os.path.exists(os.path.join(ROOT, pv) if not os.path.isabs(pv) else pv) and os.path.normpath(pv) == os.path.normpath("templates/pop-in/sample.mp4"):
        print("   the template's stand-in clip is not there yet: making it (templates/pop-in/make-sample-clip.sh); point popin.video at your own recording for a real film")
        run(["bash", "templates/pop-in/make-sample-clip.sh"], "making the stand-in clip")
    slug = film["slug"]
    outdir = os.path.join(ROOT, "out", "agent-film", slug)
    os.makedirs(os.path.dirname(outdir), exist_ok=True)
    sb = os.path.join(ROOT, "out", "agent-film", slug + ".storyboard.json")
    json.dump(film, open(sb, "w", encoding="utf-8"), indent=2)
    print("1/4 storyboard: %s (theme %s; scene lengths are derived)" % (sb, film.get("theme", "halftone")))
    run([sys.executable, "artifact/agent_film.py", sb], "the build (the message above names the key to fix)")
    page = os.path.join(outdir, "film.html")
    print("2/4 built and measured: %s" % page)
    if "--no-verify" not in args:
        out = run(["node", "tools/agent-film-verify.mjs", page], "the verify (a check failed: the film is not rendered)")
        print("3/4 verified: %s" % out.splitlines()[-1])
    else:
        print("3/4 verify SKIPPED (--no-verify): do not render a film that has not passed it")
    meta = json.load(open(os.path.join(outdir, "film.json")))
    scenes = meta["scenes"]
    print("   the film is %.1f s: %s" % (meta["duration"] / 1000, ", ".join("%s@%d" % (x["scene"], x["start"]) for x in scenes)))
    if meta["duration"] > 60000:
        print("   WARNING: %.1f s is over 60 s, the Cerebras x Kimi hackathon's maximum for a demo video. Shorten the clip (popin.ms) or drop a scene." % (meta["duration"] / 1000))
    if "--still" in args:
        if "--at" in args:
            t = int(args[args.index("--at") + 1])
        else:
            kinds = [x["scene"] for x in scenes]
            if "versus" in kinds:
                x = scenes[kinds.index("versus")]; t = x["start"] + 1500
            elif "popin" in kinds:
                x = scenes[kinds.index("popin")]; t = x["start"] + 3000
            else:
                x = scenes[1] if len(scenes) > 1 else scenes[0]; t = x["start"] + x["ms"] // 2
        t = max(0, min(t, meta["duration"] - 1))
        png = os.path.join(outdir, "still-%d.png" % t)
        run(["node", "tools/agent-film.mjs", page, "--png-at", str(t), "--out", png], "the still")
        print("4/4 a still at %d ms: %s\nLook at it. If it is right, run the same command without --still." % (t, png))
        return
    cmd = ["node", "tools/agent-film.mjs", page]
    if "--cloud" in args:
        windows = 16 if (meta.get("popin") or film.get("theme") in A.SLOW_GROUND_THEMES) else 8
        cmd += ["--engine", "lambda", "--segments", str(windows)]
        print("rendering in the cloud in %d windows" % windows)
    else:
        print("rendering locally (about a minute and a half for 20 s of film; add --cloud for the AWS function)")
    run(cmd, "the render")
    mp4 = os.path.join(outdir, slug + (".cloud.mp4" if "--cloud" in args else ".mp4"))
    print("4/4 DONE: %s" % mp4)


if __name__ == "__main__":
    main()
