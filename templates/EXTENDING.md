# Extending Cerebras Video Demos: this is a baseline, not a limit

The templates, the states and the six themes are a **starting point for your creativity**. A scene we did not draw, a look we did not make, a word in your language, a layout for your product: ask your agent (Claude Code, Codex, Cursor, Gemini, whichever you use) to build it on top of this repository. The repository is made to be extended safely: every change is held by deterministic checks, so an agent can try, break, and fix without guessing.

## Paste this to your agent

> You are working in the Cerebras Video Demos repository. Read `README.md`, then `templates/EXTENDING.md` and `templates/agent-film/README.md`. I want to extend the kit: **[what you want, e.g. "a `quote` scene that shows a customer quote with their name and a photo", or "a new theme in our brand colours", or "a vertical 9:16 layout for TikTok"]**. Follow the rules in `EXTENDING.md` (use the existing colour and weight tokens, make every component progressive and every length derived, add a staged refusal and a verifier check), show me a still of every new thing, and finish only when `bash tools/agent-film-check.sh` ends with `OK`.

## Where things live

| To change | Edit | Held by |
|---|---|---|
| a film's words, theme, scenes | your storyboard or run log (never code) | `python3 tools/make-film.py <file> --still` |
| the fixed words in another language | `words` in your storyboard | check 15 compares only numbers, so a translated unit passes |
| a **new scene** (state) | `artifact/agent_film.py` and `components/agent/film.js` (steps below) | `tools/agent-film-verify.mjs`, the fuzz, the gate |
| a **new theme** (a look) | `components/agent/agent.css` (one token block) and `THEMES` in `artifact/agent_film.py` | the verifier on every template, run per theme |
| a new component's look | `artifact/agent_components.py` | |

## The rules every extension keeps (they are why the output stays on brand and stays true)

1. **Existing colours and weights only.** Colours are tokens (`--ink`, `--accent`, `--card`, `--line`, ...) set per theme; weights are the ones the faces already use (400, 500, 600). A new look is a new TOKEN BLOCK for a theme, never a one-off colour in a scene.
2. **Progressive, never pre-sized.** A component that an LLM would render word by word takes no room until it begins: use `data-appear="<ms>"` for a box that appears, `reveal(...)` / `data-reveal` for streamed text. A box grows with its words; a bullet appears with its marker.
3. **Lengths are derived.** A scene's `ms` comes from its content (`derive_ms`): never a number a user must type. Streaming is at least 1,000 tokens a second (tokens are four thirds of the words) and exact: time = tokens / rate.
4. **The loader refuses, it never crashes.** Every key has a type and a range (`SHAPES`, `SCENE_SHAPES`, `RANGES`, `LIMITS`); a surprise is a sentence that says what to fix. Run `python3 tools/agent-film-fuzz.py` (hundreds of malformed inputs) after any change.
5. **Layout is measured, not typed.** What depends on text length (a click target, a composer's height, whether a card ends above the composer) is measured in a real browser by `tools/agent-film-measure.mjs` and the film is built twice until the two agree.
6. **Transitions and overlays have windows and checks.** A scene that is entered by morph keeps its contents invisible until the card has landed; an overlay leaves on a schedule; one loader at a time; no logo spins; the Cerebras mark never appears on a competitor.
7. **Honest.** No invented numbers, no secrets, no third party's material; a model has a stated speed or the user gives theirs.

## Add a scene (the recipe)

1. `artifact/agent_film.py`: add it to `STATES` (can it start a film, what may follow it, a one-line `what`) and to the `next` lists of the scenes that may precede it; add its content key to `SCENE_KEYS`, to `where` (which scene it belongs to) and to `SCENE_SHAPES` (every field's type; add limits to `LIMITS`).
2. Validate its content in `_load` (a refusal with the reason for each way it can be wrong), and give it a rule in `derive_ms` so its length is derived.
3. Draw it in `scene_html` with progressive components and the existing helpers (`reveal`, `thread_rows`, `window`, `docked`, `A.mark`, `A.logo`, `A.ic`). Anything that must be measured (a target, a height) goes into `tools/agent-film-measure.mjs` and is read from `MEASURED`.
4. `components/agent/film.js`: only if it needs a time-driven behaviour no existing `data-*` attribute gives (appear, reveal, show-from, scroll, blur, lerp, tokens, clock, ...); every handler computes from the time, reads no clock.
5. `tools/agent-film-check.sh`: add a staged refusal for its worst bad input; `tools/agent-film-verify.mjs`: add a check for what must always hold (the progressive build, its timing, no overlap); add it to one example storyboard in `templates/examples/`.
6. Document it: a row in the states table of `templates/agent-film/README.md`. Look at a still of it in every theme (`python3 tools/make-film.py <file> --theme <theme> --still`). Done when `bash tools/agent-film-check.sh` ends with `OK`.

## Add a theme

A theme touches these places, and the gate holds each one:

1. `components/agent/agent.css`: one token block `.ag[data-theme="mytheme"] { --window: ...; --ink: ...; --accent: ...; }`. Copy the nearest theme (`paper` is the simplest light one, `ember` the simplest dark one).
2. If the ground is dark: add the theme to the dark-window lists in the same file (`--pill-dark`, `.ag-mark-d`, and the white wordmark and partner-logo lists), or the competitor lane's pill and the logos go unreadable.
3. If the ground is drawn on a canvas (like `glow`, `bloom`, `tile`): draw it in `components/agent/ground.js` and hook it in `mount1`; seed any randomness so a frame is the same every time. Then add the name to `SLOW_GROUND_THEMES` too (the cloud renderer uses 16 windows for these).
4. `THEMES` in `artifact/agent_film.py` (the single list: the gate, the gallery and the theme demos read it) and the `theme` row in the README.
5. Rule 1 nuance: a new ground may introduce its own hues, but the window, text, logos and chips must use the theme's tokens.
6. Look: `python3 tools/make-film.py templates/project-demo/storyboard.json --theme mytheme --still`, and `--at MS` for the claim or lockup (the build prints each scene's start). The gate (`bash tools/agent-film-check.sh`) now builds and verifies every theme in `THEMES`.

## Ideas that fit the grain of the kit

A customer-quote scene; a metrics scene (numbers that dial up, a bar that grows); a code-diff scene (lines that stream in, additions green); a map or timeline pane in the browse state; a vertical 9:16 variant of the window; a language pack (`words`) for your team's language; a theme in your brand's colours; a scene that plays your own recording beside the agent's chat. Each is a small, checkable step.

The gallery of what exists today (components, themes, example videos) is the published page: https://claude.ai/artifact/VytAgnVMnn7jEPmwwsY9dz (linked from `README.md`).
