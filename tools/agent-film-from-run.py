#!/usr/bin/env python3
"""FROM A RUN TO A STORYBOARD: turn what your agent did (a run log) into a film storyboard, with every duration DERIVED, so nothing is timed by hand.

    python3 tools/agent-film-from-run.py templates/from-run/run.json [--out my-film.json]
    python3 artifact/agent_film.py my-film.json            # build (it checks the storyboard against the closed schema)

The run log is one JSON file (see templates/from-run/run.json):
    slug (optional)                 the film's folder name (default: made from the project's name)
    project, description            what the project is: they become the INTRODUCTION slide (a title and a description, no bullet points)
    model, theme, prompt            the model's name, a theme (default halftone), the user's task in the words they would type
    messages[]                      what the agent said and did, in order: {"who": "Planner", "title": "optional section title", "text": "..."},
                                    {"kind": "tool", "text": "Searched the order system"}, and "verdict": true on the final message
    answer                          {"lead": ..., "bullets": [["Bold run-in:", "the rest"], ...]}; the footer numbers are derived from the run, leave them out
    claim                           {"number": 1000, "unit": "tokens per second", "footnote": ...}
    compare (optional)              {"gpu_tps": 50, "cerebras_tps": 1000, "note": "where the GPU rate comes from"}: show the run side by side, GPU lane against Cerebras
    attachment, timer (optional)    the film's optional keys, passed through unchanged
The film is: intro slide, the typed prompt (with the pointer and the click), the run (a thread, or the two lanes if `compare`), the answer, the claim, the lockup.
Nothing in the run log is invented by this tool: it places YOUR words and derives the times.
"""
import json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "artifact")); sys.path.insert(0, os.path.join(ROOT, "tools"))
import agent_film as A  # noqa: E402


def up(ms, step=500):
    return int(math.ceil(ms / step) * step)


def _text(c):
    """the text of a chat message's content: a string, or a list of blocks (OpenAI or Anthropic style)"""
    if isinstance(c, str):
        return c.strip()
    if isinstance(c, list):
        return " ".join(_text(b.get("text") if isinstance(b, dict) else b) for b in c if isinstance(b, (str, dict)) and (isinstance(b, str) or b.get("type", "text") == "text")).strip()
    return ""


def normalize(run):
    """a chat log as it comes out of an agent framework becomes the run log's messages: {role, content, name, tool_calls} (OpenAI) or {role, content: [blocks]} (Anthropic). The first user message is the prompt (unless `prompt` is given); an assistant message is something SAID (by `name`, else the project); a tool call or a tool result is a tool line; a system message is dropped. Messages already in the run-log shape pass through"""
    msgs, prompt = [], run.get("prompt")
    for m in run["messages"]:
        if not isinstance(m, dict):
            sys.exit("the run log's messages must each be an object { ... }, not %s" % type(m).__name__)
        if "role" not in m:
            msgs.append(m); continue
        role, content, name = m.get("role"), m.get("content"), m.get("name")
        blocks = [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []
        for b in blocks:   # Anthropic tool blocks
            if b.get("type") == "tool_use":
                msgs.append({"kind": "tool", "text": "Called %s" % b.get("name", "a tool")})
            elif b.get("type") == "tool_result":
                msgs.append({"kind": "tool", "text": "Got a result from a tool"})
        text = _text(content)
        if role == "system":
            continue
        if role == "user":
            if not prompt and text:
                prompt = text
            elif text:
                msgs.append({"kind": "user", "text": text})
        elif role in ("assistant", "model"):
            if text:
                msgs.append({"who": name or run.get("project", "Agent"), "text": text})
            for tc in m.get("tool_calls") or []:
                fn = (tc.get("function") or {}) if isinstance(tc, dict) else {}
                msgs.append({"kind": "tool", "text": "Called %s" % (fn.get("name") or tc.get("name") or "a tool")})
        elif role in ("tool", "function"):
            msgs.append({"kind": "tool", "text": "Got a result from %s" % (name or "the tool")})
    run = dict(run); run["messages"] = msgs
    if prompt:
        run["prompt"] = prompt
    return run


def build(run):
    try:
        return _build(run)
    except SystemExit:
        raise
    except (TypeError, AttributeError, KeyError, ValueError, IndexError) as e:
        sys.exit("the run log has a value of the wrong shape (%s: %s): compare it with templates/from-run/README.md" % (type(e).__name__, e))


def _build(run):
    if not isinstance(run, dict):
        sys.exit("the run log must be a JSON object { ... }, not %s" % type(run).__name__)
    for k, t in (("project", str), ("description", str), ("model", str), ("prompt", str), ("slug", str), ("theme", str)):
        if k in run and not isinstance(run[k], t):
            sys.exit("the run log's %r must be text, not %s" % (k, type(run[k]).__name__))
    for k in ("messages",):
        if not isinstance(run.get(k), list) or not run.get(k):
            sys.exit("the run log needs 'messages': a non-empty list of what the agent said and did")
    if not isinstance(run.get("answer"), dict) or not str(run["answer"].get("lead", "")).strip():
        sys.exit("the run log needs 'answer': {\"lead\": the result in one line, \"bullets\": [...]}")
    for k in ("compare", "claim"):
        if k in run and not isinstance(run[k], dict):
            sys.exit("the run log's %r must be an object { ... }" % k)
    run = normalize(run)
    if not str(run.get("prompt", "")).strip():
        sys.exit("the run log needs 'prompt' (the task as the user typed it), or a first user message in 'messages'")
    for m in run["messages"]:
        if not isinstance(m, dict) or not str(m.get("text", "")).strip():
            sys.exit("every message needs non-empty text (a message is {\"who\": ..., \"text\": ...} or {\"kind\": \"tool\", \"text\": ...})")
        if m.get("kind", "say") == "say" and not str(m.get("who", "")).strip():
            sys.exit("a said message needs 'who' (the speaker's name; for one agent use its own name): %r" % str(m.get("text"))[:50])
    slug = run.get("slug") or re.sub(r"[^a-z0-9]+", "-", run["project"].lower()).strip("-") or "run"
    for k in run:
        if k in ("tagline", "points", "kicker", "footer"):
            sys.exit("the run log key %r is gone: an intro slide is a project title and a description, nothing else" % k)
    if not str(run.get("description", "")).strip():
        sys.exit("the run log needs 'description': what the project is and does, in a sentence or two")
    intro = {"title": run["project"], "description": run["description"]}
    if run.get("logo"):
        intro["logo"] = run["logo"]
    scenes = [{"scene": "intro", "ms": up(A.intro_times(intro)["end"] + A.INTRO_HOLD_MS), "intro": intro}]
    scenes.append({"scene": "typing", "ms": up(A.TYPE_START_MS + max(600, len(run["prompt"]) * 28) + A.TYPE_GAP_MS + A.POINTER_MS + A.CLICK_LEAD_MS)})
    thread = [{"kind": "user", "text": run["prompt"]}] + run["messages"]
    if run.get("compare"):
        v = {"gpu_tps": 50, **run["compare"]}
        v.setdefault("note", "")
        if A.up_to(str(run.get("model", "Kimi K3.1 Pro"))):
            v.setdefault("cerebras_tps", A.up_to(str(run.get("model", "Kimi K3.1 Pro"))))   # the model's stated speed, the same one the loader defaults to
        full = {"versus": {**A.VERSUS_DEFAULTS, **v}, "thread": thread}
        vt = A.versus_times(full)
        scenes.append({"scene": "versus", "ms": up(vt["g_film_end"] + A.DONE_HOLD_MS + 200), "versus": v, "thread": thread})
    else:
        cfg = {"tps": A.DEFAULTS["tps"]}
        _, need = A.thread_plan(cfg, {"thread": thread})
        scenes.append({"scene": "thread", "ms": up(need + 3500), "thread": thread})
    ans = dict(run["answer"])
    # the answer's footer ("Worked for N seconds", "Done in N seconds · N output tokens") is DERIVED from the run, never typed: the tokens are the run's own (the estimate used everywhere), the seconds are what the Cerebras lane takes
    total = sum(A.ntok(m["text"]) + (A.ntok(m["title"]) if m.get("title") else 0) for m in run["messages"] if m.get("kind") != "user") + A.answer_tokens({"lead": ans["lead"], "bullets": ans.get("bullets", [])})
    cps = float((run.get("compare") or {}).get("cerebras_tps", A.up_to(str(run.get("model", ""))) or A.VERSUS_DEFAULTS["cerebras_tps"]))
    ans.setdefault("footer_seconds", max(1, int(round(total / cps))))
    ans.setdefault("footer_tokens", "%.1fk" % (total / 1000.0))
    ans["stream_ms"] = A.answer_tokens({"lead": ans["lead"], "bullets": ans.get("bullets", [])})   # exactly the Cerebras rate
    scenes.append({"scene": "answer", "ms": 6500, "answer": ans})
    scenes += [{"scene": "claim", "ms": 3500}, {"scene": "lockup", "ms": 3000}]
    film = {"slug": slug, "why": "Built from a run log by tools/agent-film-from-run.py: %s." % run["project"], "theme": run.get("theme", "halftone"), "model": run["model"], "prompt": run["prompt"],
            "claim": {"footnote": "*Demo shown with mock data.", **run.get("claim", {"number": A.up_to(run["model"]), "unit": "tokens per second"} if A.up_to(run["model"]) else {"unit": "tokens per second"})}, "scenes": scenes}
    for k in ("attachment", "timer", "partner_logo", "words"):
        if k in run:
            film[k] = run[k]
    return film


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    run = json.load(open(sys.argv[1], encoding="utf-8"))
    film = build(run)
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(ROOT, "out", "agent-film", film["slug"] + ".storyboard.json")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(film, open(out, "w", encoding="utf-8"), indent=2)
    A.load(out)   # refuses, with the reason, anything the closed schema cannot play
    print("%s  (%.1f s)\nnext: python3 artifact/agent_film.py %s" % (out, sum(s["ms"] for s in film["scenes"]) / 1000, out))


if __name__ == "__main__":
    main()
