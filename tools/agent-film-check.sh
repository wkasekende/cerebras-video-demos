#!/usr/bin/env bash
# THE AGENT FILM TEMPLATE'S GATE: the storyboards build, the closed schema refuses what it cannot play, and a real Chrome photographs a moment of each film.
#   bash tools/agent-film-check.sh
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
refuse() { local why="$1" body="$2"; echo "$body" > "$T/r.json"; if out="$(python3 artifact/agent_film.py "$T/r.json" 2>&1)"; then echo "  NOT REFUSED: $why"; return 1; fi; echo "$out" | grep -q "storyboard refused" || { echo "  wrong failure for: $why"; echo "$out" | tail -2; return 1; }; }
echo "▸ [agent film] the schema refuses what it cannot play"
refuse "an unknown key" '{"slug":"x","model":"M","prompt":"p","colour":"red","scenes":[{"scene":"claim","ms":1000}]}'
refuse "a scene that does not exist" '{"slug":"x","model":"M","prompt":"p","scenes":[{"scene":"dance","ms":1000}]}'
refuse "a scene too short" '{"slug":"x","model":"M","prompt":"p","scenes":[{"scene":"claim","ms":100}]}'
refuse "an unknown theme" '{"slug":"x","model":"M","prompt":"p","theme":"neon","scenes":[{"scene":"claim","ms":1000}]}'
refuse "a pop-in with no video" '{"slug":"x","model":"M","prompt":"p","scenes":[{"scene":"popin","ms":1000}]}'
refuse "a scene that cannot follow the one before it" '{"slug":"x","model":"M","prompt":"p","scenes":[{"scene":"lockup","ms":1000},{"scene":"typing","ms":1000}]}'
refuse "a planned state that is not built" '{"slug":"x","model":"M","prompt":"p","scenes":[{"scene":"ask","ms":1000}]}'
refuse "a film that starts on a scene that cannot start one" '{"slug":"x","model":"M","prompt":"p","scenes":[{"scene":"turn","ms":1000}]}'
refuse "a pop-in whose video is missing" '{"slug":"x","model":"M","prompt":"p","popin":{"video":"/nonexistent.mp4"},"scenes":[{"scene":"popin","ms":1000}]}'
refuse "a thread slower than Cerebras speed" '{"slug":"x","model":"M","prompt":"p","scenes":[{"scene":"welcome","ms":1000},{"scene":"thread","ms":9000,"tps":200,"thread":[{"kind":"say","who":"A","text":"hello there"}]}]}'
refuse "a Cerebras lane under 1,000 tokens a second" '{"slug":"x","model":"M","prompt":"p","scenes":[{"scene":"welcome","ms":1000},{"scene":"versus","ms":9000,"versus":{"gpu_tps":50,"cerebras_tps":900,"note":"n"},"thread":[{"kind":"say","who":"A","text":"hello there"}]}]}'
refuse "a GPU lane faster than the Cerebras lane" '{"slug":"x","model":"M","prompt":"p","scenes":[{"scene":"welcome","ms":1000},{"scene":"versus","ms":9000,"versus":{"gpu_tps":2000,"cerebras_tps":1500,"note":"n"},"thread":[{"kind":"say","who":"A","text":"hello there"}]}]}'
refuse "a GPU range that does not hold the GPU rate" '{"slug":"x","model":"M","prompt":"p","scenes":[{"scene":"welcome","ms":1000},{"scene":"versus","ms":9000,"versus":{"gpu_tps":60,"gpu_tps_range":[70,120],"cerebras_tps":1000,"note":"n"},"thread":[{"kind":"say","who":"A","text":"hello there"}]}]}'
refuse "a versus with no note on where the GPU rate comes from" '{"slug":"x","model":"M","prompt":"p","scenes":[{"scene":"welcome","ms":1000},{"scene":"versus","ms":9000,"thread":[{"kind":"say","who":"A","text":"hello there"}]}]}'
refuse "an answer streamed under 1,000 tokens a second" '{"slug":"x","model":"M","prompt":"p","scenes":[{"scene":"welcome","ms":1000},{"scene":"answer","ms":9000,"answer":{"lead":"a b c d e f g h i j k l m n o p q r s t","stream_ms":5000}}]}'
refuse "a typing scene too short for the pointer and the click" '{"slug":"x","model":"M","prompt":"p","scenes":[{"scene":"typing","ms":1500},{"scene":"welcome","ms":1000}]}'
refuse "an attachment with no title" '{"slug":"x","model":"M","prompt":"p","attachment":{"meta":"PDF"},"scenes":[{"scene":"claim","ms":1000}]}'
refuse "a browse scene with no pages" '{"slug":"x","model":"M","prompt":"p","scenes":[{"scene":"welcome","ms":1000},{"scene":"browse","ms":9000,"browse":{"pages":[]}}]}'
refuse "an ask with no reply" '{"slug":"x","model":"M","prompt":"p","scenes":[{"scene":"welcome","ms":1000},{"scene":"ask","ms":9000,"ask":{"question":"Which?"}}]}'
refuse "a fast forward below 1" '{"slug":"x","model":"M","prompt":"p","scenes":[{"scene":"welcome","ms":1000},{"scene":"versus","ms":20000,"versus":{"fast_forward":0.5,"note":"n"},"thread":[{"kind":"say","who":"A","text":"hello there"}]}]}'
refuse "a cut straight after typing (the morph is not a cut)" '{"slug":"x","model":"M","prompt":"p","scenes":[{"scene":"typing","ms":4500},{"scene":"welcome","ms":1000,"cut":true}]}'
refuse "a Kimi claim above the stated 1,000 tokens a second" '{"slug":"x","model":"Kimi K3.1 Pro","prompt":"p","claim":{"number":2000},"scenes":[{"scene":"claim","ms":1000}]}'
refuse "a Kimi Cerebras lane above the stated 1,000 tokens a second" '{"slug":"x","model":"Kimi K3.1 Pro","prompt":"p","scenes":[{"scene":"welcome","ms":1000},{"scene":"versus","ms":9000,"versus":{"gpu_tps":50,"cerebras_tps":1500,"note":"n"},"thread":[{"kind":"say","who":"A","text":"hello there"}]}]}'
refuse "a typing scene with no prompt" '{"slug":"x","model":"M","scenes":[{"scene":"typing"},{"scene":"welcome"}]}'
refuse "an intro with a bullet list" '{"slug":"x","model":"M","scenes":[{"scene":"intro","intro":{"title":"T","description":"D","points":["a","b"]}}]}'
refuse "a text that looks like an API key" "$(printf '{"slug":"x","model":"M","prompt":"use %s now","scenes":[{"scene":"welcome","ms":1000}]}' "sk-""abcdefghijklmnopqrstuvwxyz123456")"
refuse "a Cerebras key in a message" "$(printf '{"slug":"x","model":"M","prompt":"p","scenes":[{"scene":"welcome","ms":1000},{"scene":"thread","ms":9000,"thread":[{"who":"A","text":"my key %s"}]}]}' "csk-""abcdefghijklmnopqrstuvwx")"
echo "  twenty-six refusals"
echo "▸ [agent film] the fuzz: hundreds of malformed and awkward inputs, each accepted or refused with a reason, none a crash"
python3 tools/agent-film-fuzz.py | tail -3 || exit 1
echo "▸ [agent film] build and photograph the template, then the pop-in template"
bash templates/pop-in/make-sample-clip.sh > /dev/null
for sb in templates/agent-film/storyboard.json templates/pop-in/storyboard.json; do
  slug="$(python3 -c "import json,sys;print(json.load(open('$sb'))['slug'])")"
  python3 artifact/agent_film.py "$sb" > /dev/null
  vout="$(node tools/agent-film-verify.mjs "out/agent-film/$slug/film.html")" || { echo "$vout"; exit 1; }
  echo "  $slug: $(echo "$vout" | tail -1)"
  node tools/agent-film.mjs "out/agent-film/$slug/film.html" --png-at 9500 --out "$T/$slug.png" 2> /dev/null
  size="$(stat -c %s "$T/$slug.png")"
  [ "$size" -gt 60000 ] || { echo "  $slug: the still is $size bytes: blank?"; exit 1; }
  echo "  $slug: built and photographed ($size bytes)"
done
echo "▸ [agent film] the four examples: build, verify, length 40-60 s (stand-in clips made first)"
mkdir -p out/standin
for name in docs dashboard code; do [ -f "out/standin/$name.mp4" ] || node tools/standin-clip.mjs --kind "$name" --out "out/standin/$name.mp4" > /dev/null 2>&1 || { echo "could not make the stand-in clip $name"; exit 1; }; done
for sb in templates/examples/*.json; do
  slug="$(python3 -c "import json;print(json.load(open('$sb'))['slug'])")"
  python3 artifact/agent_film.py "$sb" > /dev/null
  python3 - "out/agent-film/$slug/film.json" <<'PY' || exit 1
import json,sys
f=json.load(open(sys.argv[1])); d=sum(s["ms"] for s in f["scenes"])/1000
assert 40<=d<=60,(sys.argv[1],d)
PY
  vout="$(node tools/agent-film-verify.mjs "out/agent-film/$slug/film.html")" || { echo "$vout"; exit 1; }
  echo "  $slug: $(echo "$vout" | tail -1)"
done
echo "▸ [agent film] the project templates: a clip with an intro slide, and a run log in both modes"
python3 tools/agent-film-from-run.py templates/from-run/run.json --out "$T/run-thread.json" > /dev/null
python3 - "$T" <<'PY'
import json,sys
r=json.load(open("templates/from-run/run.json")); r["compare"]={"gpu_tps":50,"note":"Illustrative rates."}; r["project"]="Acme Support Agent Compare"
json.dump(r,open(sys.argv[1]+"/run-compare-in.json","w"))
PY
python3 tools/agent-film-from-run.py "$T/run-compare-in.json" --out "$T/run-compare.json" > /dev/null
for sb in templates/project-demo/storyboard.json "$T/run-thread.json" "$T/run-compare.json"; do
  slug="$(python3 -c "import json,sys;print(json.load(open('$sb'))['slug'])")"
  python3 artifact/agent_film.py "$sb" > /dev/null
  vout="$(node tools/agent-film-verify.mjs "out/agent-film/$slug/film.html")" || { echo "$vout"; exit 1; }
  echo "  $slug: $(echo "$vout" | tail -1)"
done
echo "▸ [agent film] the guided command, both inputs and a theme each (make-film.py --still builds, measures, verifies and photographs)"
for pair in "templates/from-run/run.json paper" "templates/project-demo/storyboard.json ember"; do
  set -- $pair
  out="$(python3 tools/make-film.py "$1" --theme "$2" --still)" || { echo "$out"; exit 1; }
  echo "  $1 ($2): $(echo "$out" | grep -c '^[1-4]/4') steps"
done
echo "▸ [agent film] EVERY theme builds and verifies (project-demo in each theme in THEMES): a new theme is checked here without anyone remembering to add it"
for th in $(python3 -c "import sys; sys.path.insert(0,'artifact'); import agent_film as A; print(' '.join(A.THEMES))" 2>/dev/null); do
  out="$(python3 tools/make-film.py templates/project-demo/storyboard.json --theme "$th" --still)" || { echo "$out"; exit 1; }
  echo "  $th: $(echo "$out" | grep '^3/4')"
done
echo "OK"
