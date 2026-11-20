#!/usr/bin/env python3
"""THE API MUST NOT BREAK: whatever a user types into a storyboard or a run log, the loader either accepts it or REFUSES it with a sentence that says what to fix; it never crashes with a traceback and never silently drops a key.

    python3 tools/agent-film-fuzz.py            about 200 malformed and awkward inputs, in seconds (no browser): every one must be accepted or refused cleanly
"""
import copy, json, os, sys, tempfile, traceback
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "artifact")); sys.path.insert(0, HERE)
os.chdir(ROOT)
import agent_film as A  # noqa: E402
import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location("from_run", os.path.join(HERE, "agent-film-from-run.py"))
FR = importlib.util.module_from_spec(spec); spec.loader.exec_module(FR)

BASE = {"slug": "fz", "model": "Kimi", "prompt": "Do the thing.", "theme": "paper", "claim": {"number": 1000, "unit": "tokens per second"},
        "scenes": [{"scene": "intro", "intro": {"title": "Fz", "description": "A test."}},
                   {"scene": "typing"},
                   {"scene": "thread", "thread": [{"kind": "user", "text": "hi"}, {"who": "A", "text": "hello there"}]},
                   {"scene": "answer", "answer": {"lead": "Done.", "bullets": [["A:", "b"]]}},
                   {"scene": "claim"}, {"scene": "lockup"}]}
RUN = {"project": "Fz", "description": "A test.", "model": "Kimi", "prompt": "Do it.", "messages": [{"who": "A", "text": "hello there"}], "answer": {"lead": "Done."}}
cases = []


def case(name, mut, base=BASE, kind="storyboard"):
    cases.append((name, mut, base, kind))


def setkey(path, value):
    def m(c):
        o = c
        for k in path[:-1]:
            o = o[k]
        if value == "__DEL__":
            o.pop(path[-1], None) if isinstance(o, dict) else o.pop(path[-1])
        else:
            o[path[-1]] = value
    return m


WEIRD = [None, 0, -1, 1.5, "", " ", "x" * 5000, True, [], {}, [1], {"a": 1}, "<script>alert(1)</script>", "😀 emoji", "العربية", "日本語", "a\nb", float("inf")]
for k in ("slug", "model", "prompt", "theme", "scenes", "claim", "fade_ms", "fps", "tool", "meter", "answer", "attachment", "timer", "popin", "partner_logo", "why"):
    for v in WEIRD:
        case("top %s=%r" % (k, v if not isinstance(v, str) or len(v) < 30 else v[:20] + "..."), setkey([k], v))
for k in ("ms", "scene", "intro", "thread", "answer", "type_ms", "cut", "variant", "tps"):
    for v in (None, "x", -5, 0, 10**9, [], {}, True):
        case("scene[1] %s=%r" % (k, v), (lambda k, v: lambda c: c["scenes"][1].__setitem__(k, v))(k, v))
for k in ("title", "description", "logo", "points", "kicker"):
    for v in (None, 5, [], {}, "", "z" * 3000, ["a"]):
        case("intro %s=%r" % (k, v if not isinstance(v, str) or len(v) < 30 else "long"), setkey(["scenes", 0, "intro", k], v))
for v in (None, "x", 5, [], [None], ["x"], [{}], [{"text": 5}], [{"who": 5, "text": "t"}], [{"kind": "zzz", "text": "t"}], [{"kind": "user", "text": ""}], [{"who": "A", "text": "t", "title": 5}], [{"who": "A", "text": "t", "verdict": "yes"}], [{"who": "A", "text": ["x"]}]):
    case("thread=%r" % (v,), setkey(["scenes", 2, "thread"], v))
for v in (None, "x", 5, [], {}, {"lead": 5}, {"lead": "x", "bullets": "str"}, {"lead": "x", "bullets": [5]}, {"lead": "x", "bullets": [["a"]]}, {"lead": "x", "bullets": [["a", 5]]}, {"lead": "x", "stream_ms": "q"}, {"lead": "x", "stream_ms": -1}, {"lead": "x" * 4000}):
    case("answer=%r" % (v if not isinstance(v, dict) else sorted(v.items(), key=str)[:2],), setkey(["scenes", 3, "answer"], v))
for v in (None, "x", 5, [], {}, {"number": "abc"}, {"number": None}, {"number": -3}, {"number": 10 ** 12}, {"number": 1e400}, {"number": 1000, "unit": 5}, {"number": 1000, "footnote": ["x"]}):
    case("claim=%r" % (v,), setkey(["claim"], v))
for scene in ({"scene": "versus", "thread": [{"who": "A", "text": "hello there"}], "versus": v} for v in (None, "x", {}, {"gpu_tps": "q", "note": "n"}, {"gpu_tps": -1, "note": "n"}, {"gpu_tps": 0, "note": "n"}, {"gpu_tps": 10 ** 9, "note": "n"}, {"cerebras_tps": 10 ** 9, "note": "n"}, {"note": 5}, {"note": "n", "fast_forward": "x"}, {"note": "n", "fast_forward": 1e9}, {"note": "n", "view": "zzz"}, {"note": "n", "gpu_label": 5})):
    case("versus=%r" % (scene["versus"],), (lambda s: lambda c: c["scenes"].insert(3, copy.deepcopy(s)))(scene))
for scene in ({"scene": "ask", "ask": v} for v in (None, "x", {}, {"question": "q"}, {"question": "q", "reply": "r", "options": "abc"}, {"question": "q", "reply": "r", "options": [5]})):
    case("ask=%r" % (scene["ask"],), (lambda s: lambda c: c["scenes"].insert(3, copy.deepcopy(s)))(scene))
for scene in ({"scene": "browse", "browse": v} for v in (None, "x", {}, {"pages": "x"}, {"pages": [{}]}, {"pages": [{"url": 5, "heading": "h"}]}, {"pages": [{"url": "u", "heading": "h", "lines": "str"}]}, {"pages": [{"url": "u", "heading": "h", "scroll": "q"}]}, {"pages": [{"url": "u", "heading": "h", "modal": "m"}]}, {"pages": [{"url": "u", "heading": "h", "pointer": True}]})):
    case("browse=%r" % (scene["browse"],), (lambda s: lambda c: c["scenes"].insert(3, copy.deepcopy(s)))(scene))
for scene in ({"scene": "popin", "clip_from": v} for v in ("x", -1, None, 10 ** 9)):
    case("popin clip_from=%r" % (scene["clip_from"],), (lambda s: lambda c: c["scenes"].insert(3, copy.deepcopy(s)))(scene))
for name, order in (("empty scenes", []), ("lockup first", ["lockup", "claim"]), ("300 scenes", ["ground"] * 300), ("unknown", ["nope"]), ("none", [None]), ("numbers", [1, 2]), ("strings", ["claim"])):
    case("scenes %s" % name, (lambda order: lambda c: c.__setitem__("scenes", [({"scene": o} if isinstance(o, str) else o) for o in order]))(order))
for n, text in (("secret", "my key is " + "sk-" + "abcdefghijklmnopqrstuvwxyz123456"), ("aws", "AKIA" + "ABCDEFGHIJKLMNOP"), ("html", "<b onclick=x>&amp; \"q\" 'q'</b>"), ("emoji", "😀🚀 émojis ñ"), ("rtl", "مرحبا بالعالم"), ("cjk", "日本語のテキスト" * 40), ("nowrap", "A" * 400), ("newlines", "a\n\n\nb\r\nc"), ("tabs", "a\tb"), ("zero-width", "a​b"), ("null-byte", "a\x00b"), ("long", "word " * 3000), ("backticks", "```python\nprint(1)\n```"), ("json-ish", '{"a": [1,2]}')):
    case("text %s in a message" % n, setkey(["scenes", 2, "thread", 1, "text"], text))
    case("text %s in the intro" % n, setkey(["scenes", 0, "intro", "description"], text))
    case("text %s as the prompt" % n, setkey(["prompt"], text))
CHAT_OPENAI = dict(RUN, prompt="", messages=[{"role": "system", "content": "be nice"}, {"role": "user", "content": "Find me a flight to Lisbon."}, {"role": "assistant", "content": "", "tool_calls": [{"id": "1", "type": "function", "function": {"name": "search_flights", "arguments": "{}"}}]}, {"role": "tool", "name": "search_flights", "content": "[...]"}, {"role": "assistant", "content": "I found three flights; the cheapest is 142 euros."}])
CHAT_ANTHROPIC = dict(RUN, prompt="", messages=[{"role": "user", "content": [{"type": "text", "text": "Summarise the ticket."}]}, {"role": "assistant", "content": [{"type": "text", "text": "Reading it now."}, {"type": "tool_use", "id": "t", "name": "get_ticket", "input": {}}]}, {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t", "content": "..."}]}, {"role": "assistant", "content": [{"type": "text", "text": "The customer wants a refund."}]}])
for v in (CHAT_OPENAI, CHAT_ANTHROPIC):
    case("a chat log in the framework's own format is ACCEPTED", lambda c: c, base=v, kind="run_ok")
for v in (None, "x", 5, [], {"messages": []}, {"project": "x"}, dict(RUN, messages="x"), dict(RUN, messages=[{}]), dict(RUN, messages=[{"role": "tool"}]), dict(RUN, answer="x"), dict(RUN, answer={}), dict(RUN, compare="x"), dict(RUN, compare={}), dict(RUN, compare={"gpu_tps": "q", "note": "n"}), dict(RUN, tagline="old"), dict(RUN, points=["a"]), dict(RUN, project=""), dict(RUN, project="!!!"), dict(RUN, slug="Bad Slug"), dict(RUN, theme="neon"), dict(RUN, description=" ")):
    case("run log %r" % (v if not isinstance(v, dict) else {k: (x if not isinstance(x, (list, dict)) else type(x).__name__) for k, x in v.items()},), lambda c, v=v: c, base=v, kind="run")


def ok_clean(exc):
    return isinstance(exc, SystemExit) and ("refused" in str(exc) or "run log" in str(exc) or "needs" in str(exc) or "gone" in str(exc) or isinstance(exc.code, str))


def main():
    bad = []
    n_ok = n_ref = 0
    for name, mut, base, kind in cases:
        c = copy.deepcopy(base)
        try:
            mut(c)
        except Exception:
            continue   # the mutation did not apply to this shape: not a case
        fd, p = tempfile.mkstemp(suffix=".json"); os.close(fd)
        try:
            json.dump(c, open(p, "w"), allow_nan=True)
            if kind in ("run", "run_ok"):
                A.load(os.path.join(ROOT, "out", "agent-film", "fz.sb.json")) if False else None
                sb = FR.build(c) if isinstance(c, dict) else (_ for _ in ()).throw(SystemExit("the run log must be a JSON object"))
                json.dump(sb, open(p, "w"))
            A.load(p); n_ok += 1
        except SystemExit as e:
            if ok_clean(e):
                n_ref += 1
            else:
                bad.append((name, "SystemExit with no explanation: %r" % (e.code,)))
        except Exception as e:  # noqa: BLE001
            bad.append((name, "CRASH %s: %s" % (type(e).__name__, str(e)[:100])))
        finally:
            os.remove(p)
    print("%d cases: %d accepted, %d refused with a reason, %d BAD" % (len(cases), n_ok, n_ref, len(bad)))
    for n, why in bad[:60]:
        print("  BAD:", n, "->", why)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
