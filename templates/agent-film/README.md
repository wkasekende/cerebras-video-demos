# Agent film template: from a storyboard to an MP4

> **New here?** Read [`../START-HERE.md`](../START-HERE.md) (two paths, six looks, one command: `python3 tools/make-film.py <input.json> --theme <theme> --still`). **An AI agent doing it for a user?** Give it [`../AGENT-INSTRUCTIONS.md`](../AGENT-INSTRUCTIONS.md). This file is the reference: every key, state and rule.

Everything you need to make a Cerebras-styled agent demo film (a typed prompt, the app window, a turn, an answer, a claim, the closing lockup), or to **pop your own video in**
(`templates/pop-in/`). It is built from the shared components and themes in `components/agent/` and `artifact/agent_components.py`; a film holds only your words.

## Start here: put YOUR project's agent in a film (for a person or for another agent)

Pick the row that matches what you HAVE. Every row ends in the same two commands (build, then render); only the input differs.

| You have | Make | Template | Opener |
|---|---|---|---|
| a screen recording of your agent working | **put a video inside**: your clip as the whole window | `templates/project-demo/storyboard.json` | **intro slide**: what the project is |
| what the agent did, as text (messages, tool calls, an answer) but no recording | **recreate it as HTML**: the run played in the house components (and, if you want, GPU against Cerebras) | `python3 tools/make-film.py run.json --still` (key guide: [`from-run/README.md`](../from-run/README.md)) | **intro slide**, then the typed prompt |

**The opener decides the film.** A film that is NOT a rebuild opens with an `intro` scene: a **title** and a **description** (and an optional logo), nothing else, no bullet points, built up progressively on the theme's ground. The typed-prompt opener (`typing`, with the pointer's click and the morph into the window) belongs to rebuilds and to runs where the prompt itself is the story. `intro` may also be followed by `typing`.

**DO**
- Say what the project IS in the intro description in a sentence or two a stranger could repeat; the intro is a title and a description, no bullet points.
- Put the SAME words in the storyboard that the agent really said and did (`tools/make-film.py` places your words and derives every time; it invents nothing).
- Keep the Cerebras side honest: `cerebras_tps` is at least 1,000, the GPU rate has a `note` saying where it comes from or that it is illustrative, and the numbers in a claim have a footnote.
- Use the theme's own look: change the words, `theme`, your logo (SVG), nothing else. Colours and weights are not keys on purpose.
- Make the film long enough to read and short enough to watch: an intro holds at least 2.2 s after it builds; 20 to 60 s is the range; fill time with the demo moving (a clip, a scroll) or `versus`, never with slower text.
- Run `node tools/agent-film-verify.mjs film.html` before you render; it must say `0 failed`. Take a still (`--png-at`) and look at it.

**DON'T**
- Don't type your own timings: the intro, the thread, the versus scene and the typing scene tell you the least `ms` they need (the loader refuses a shorter one, and the converter derives them).
- Don't show a real company's page, logo or customer data you do not have the right to show; browse pages are generic stand-ins on purpose. Don't use a screen recording with a person's private data.
- Don't put the Cerebras mark on a competitor, or recolour the competitor lane: it is desaturated by the system.
- Don't add a second video path (your own HTML, your own CSS): if the system cannot play it, say so in an issue; a new state goes into `STATES` first.
- Don't render before it verifies, and don't render glow, bloom or tile in 8 cloud windows (use 16 to 20).

**For an AI agent doing this for a user.** Inputs to collect: the project's name, a description (a sentence or two), the model name, the user's task as a prompt, then either the clip's path or the run (messages, tool calls, the answer). Write `run.json` (see `templates/from-run/README.md`) or edit `templates/project-demo/storyboard.json`; then `python3 tools/make-film.py <file> --theme <theme> --still`, which runs the converter, the build, the measure, the verify and the photograph itself (those are what it calls, not steps you run); look at the still; then the same command without `--still`. If a command refuses, the message names the key and the allowed values: fix the JSON, do not work around it.

## Quick start (from a fresh checkout, about three minutes)

```bash
npm install                                   # puppeteer + a Chrome for Testing (tools/chrome.mjs finds it)
# also needed on PATH: python3 (3.8+), ffmpeg, ffprobe, and (for pop-in) nothing else
python3 tools/make-film.py templates/agent-film/storyboard.json --still   # builds, measures, verifies, photographs: look at it
python3 tools/make-film.py templates/agent-film/storyboard.json          # -> out/agent-film/acme-demo/acme-demo.mp4  (1920x1080, 30 fps, H.264)
# (what make-film.py runs, one step at a time: artifact/agent_film.py builds, tools/agent-film-verify.mjs checks, tools/agent-film.mjs renders)
```

A still at one moment instead of the film: `node tools/agent-film.mjs out/agent-film/acme-demo/film.html --png-at 9500`. A contact sheet (one frame a second): add `--contact`.

## The storyboard

`storyboard.json` is the whole input. Unknown keys are refused. Required: `slug`, `model`, `scenes` (and `prompt` when a scene shows the typed task). Everything else has a default.

| key | meaning |
|---|---|
| `slug` | lowercase letters, digits, dashes; names the output folder `out/agent-film/<slug>/` |
| `why` | optional free text: what the film is for (kept in the file, not shown) |
| `ms` (on a scene) | **optional**: a scene's length is DERIVED from its content (an intro: the time to build and be read; a clip: its own length; a thread or versus: its text at its rate); give `ms` only to hold a scene longer, the loader refuses less than the content needs |
| `theme` | one of `halftone` (default), `glow`, `ember`, `paper`, `bloom`, `tile`: the look (a ground and a window). Never invent new colours or weights: pick a theme. |
| `model` | the model's name as it should read (the pill, the title bar, the claim's headline) |
| `prompt` | the user's prompt (typed in the first scene, shown in the bubble) |
| `words` | **optional**: the few fixed words the film draws, in your language: `up_to` ("Up to"), `done`, `sec`, `tokens`, `tokens_per_s`, `ready`, `analyzing`, `thinking`, `final_answer`, `follow_up`, `placeholder`, `welcome_q`, `preparing`, `worked_for` ("Worked for {n} seconds"), `done_in` ("Done in {s} seconds · {t} output tokens"), `assistant`, `just_now`, `ttft`. Only the words you give are replaced. Numbers stay in the 1,000 style; your own text is never touched |
| `partner_logo` | the logo beside the Cerebras logo in the closing lockup (it replaces Kimi's): an SVG file (SVG, PNG, JPG or WebP allowed); its black shapes (`fill="black"`) turn white where the theme calls for it. **Kimi's logo is the default** for a Kimi film where the Kimi kit is present; where it is not (a public checkout), the lockup shows the Cerebras logo alone |
| `tool.name` | the tool line's words ("Using Browser") |
| `meter` | `seconds`, `tokens`, `rate` ("1,000 toks/s"), `ttft` ("31 ms"): the live meter and the answer's footer chip |
| `answer` | `lead` (the first line), `bullets` (each a string, or `["Bold run-in:", "the rest"]`), `footer_seconds`, `footer_tokens` |
| `claim` | `number` (it counts up to this), `unit` ("tokens per second"), `footnote` |
| `popin` | only with a `popin` scene: `video` (a path to your clip, absolute is fine), `speed` (1), `fit` (`auto`: fill if the clip is 16:9 within 3%, else show it whole with black bars; or `cover`, `contain`) |
| `attachment` | **optional**: `{title, meta, thumb}`. Absent, nothing is drawn for it. Present, a stack of pages slides in beside the typed prompt and a card rides under the user's bubble in every scene (with no `thumb` a plain page is drawn) |
| `timer` | **optional**, `true`: the elapsed-time pill centred in the title bar, counting from the first turn and stopping where the answer begins |
| `tps` | tokens a second a thread streams at: the Cerebras rate, **at least 1,000** (the default); a slower stream is refused except as the GPU lane of a `versus` scene |
| `fade_ms` | the crossfade into each scene (450) |
| `fps` | 30 |
| `scenes` | a list of `{ "scene": ..., "ms": ... }` in order; `ms` is at least 600 |

## The states, and what may follow what

A film is a list of scenes, and the scenes are **states of a small machine written in code** (`STATES` in `artifact/agent_film.py`). The loader refuses a storyboard whose first scene or any change between scenes is not in the table, and
says what would be allowed instead. How a change is drawn is not free either.

| scene | may start a film | may be followed by | what it shows |
|---|---|---|---|
| `typing` | yes | `welcome`, `turn`, `answer`, `thread`, `popin` | the prompt types into the hero composer on the ground (`type_ms` sets how long) |
| `intro` | yes | `typing`, `welcome`, `turn`, `answer`, `thread`, `versus`, `popin`, `browse`, `ask`, `ground`, `claim`, `lockup` | **a title and a description** (and an optional logo), then the **Cerebras × model logos** under the description (Kimi's logo for a Kimi film, your `partner_logo` if you set one, otherwise the Cerebras logo alone; `intro.lockup: false` hides them): what the project is, built up on the theme's ground. The opener for a film that is not a rebuild |
| `welcome` | yes | `turn`, `answer`, `thread`, `claim`, `lockup` | the window at rest: the mark, the question, the composer holding the prompt |
| `turn` | no | `answer`, `thread`, `claim`, `lockup` | the user's bubble, "Preparing this turn" (the one loading indicator), the tool line, the meter |
| `answer` | no | `turn`, `thread`, `popin`, `claim`, `lockup` | "Worked for N seconds", the answer card with your bullets, the footer, the finished composer |
| `popin` | yes | `thread`, `turn`, `answer`, `claim`, `lockup` | **your own 16:9 clip, with rounded corners, replaces the white window** |
| `thread` | no | `thread`, `turn`, `answer`, `popin`, `claim`, `lockup` | a conversation between agents: messages (`say` with a `who`, `tool`, `user`) each stream in word by word and the list scrolls as it grows; `ms` must cover the schedule (the loader says how long it needs) |
| `versus` | no | `versus`, `thread`, `turn`, `answer`, `popin`, `claim`, `lockup` | side by side: the same conversation in a GPU lane and a Cerebras lane, each streaming at its own tokens a second with a live token count, a clock pill and a DONE card (the source video's layout: Cerebras on the left). Cerebras is never under 1,000; the GPU rate is yours (`versus.gpu_tps`) and `versus.note` (required) says where it comes from or that it is illustrative. `versus.view: "answer"` draws the prompt bubble and answer card in both lanes instead of a thread |
| `ask` | no | `turn`, `thread`, `versus`, `answer`, `ground`, `claim`, `lockup` | the assistant asks a question (`ask: {question, options, reply}`), the options appear one by one, the turn waits, the user's reply arrives and "Preparing this turn" ticks |
| `second-turn` | no | `answer`, `thread`, `versus`, `turn`, `integration`, `ground`, `claim`, `lockup` | the first exchange stays; `second: {prompt}` is typed into the docked composer, the pointer presses send, the conversation scrolls up under the new bubble |
| `integration` | no | `ground`, `claim`, `lockup` | the window defocuses and a white card builds in over it: `integration: {tag, title, badge, chips, body}`, every part progressive |
| `browse` | no | `turn`, `thread`, `versus`, `answer`, `ask`, `ground`, `claim`, `lockup` | the chat narrows left, the browser pane slides in: `browse: {pages: [{url, title, heading, lines, button, scroll, modal, pointer, ms}]}`; tabs, address bar, page changes, an optional scroll, modal and pointer click. Pages are generic stand-ins, never a real site. Not directly after `typing` |
| `ground` | yes | `typing`, `popin`, `claim`, `lockup` | the ground alone: the blank beat |
| `claim` | yes | `lockup` | the model's name, the claim's number dialling up, the footnote |
| `lockup` | yes | nothing | the Cerebras logo, a hairline, your logo: the end |

**Transitions.** There are two, and the rule is in code (`MORPH_FROM`): after `typing`, the composer **morphs**: it grows, its corners and colour change, and it *becomes* the white base of the next scene (the window, or your
video) while its text fades out and the next scene's contents fade in. Every other change is a **crossfade** of `fade_ms`. **Numbers dial**: every counting number (the claim, the meter, the footer, "Worked for N seconds") reads 0 when its scene
appears and dials up to its final value. **One loader**: a `turn` scene has exactly one spinner on screen, every other scene none; the Cerebras mark and a brand logo never spin. **No audio states**: the film has no audio, so
no microphone icon appears anywhere.

**Future states.** Every state the reference videos show is built (`FUTURE_STATES` is empty). A state seen in a NEW reference video goes into `FUTURE_STATES` first, with the reason, and a storyboard naming it is refused with that reason; then it goes into `STATES` (with its `start` and `next`), is drawn in `scene_html`, and `tools/agent-film-verify.mjs` holds it to the same rules.

## Deterministic checks

`node tools/agent-film-verify.mjs out/agent-film/<slug>/film.html` is run for every template by `bash tools/agent-film-check.sh`. It uses no eye: about 150 equalities and numbers. The scenes and times are `film.json`'s; every
transition is the declared kind; a moment painted, then others, then the first again, gives the same page state (every style, text, animation clock) and, within a 80-pixel anti-aliasing allowance, the same pixels; the middle of each scene
shows only that scene; at most one spinner is ever on screen; no logo is animated; there is no microphone icon; every dial reads 0 as it starts and its final text once it finishes; each morph begins on the composer's rectangle, ends on
the target's and is monotone between, and the card is gone afterwards. A failure prints the check's number and what differed, and exits non-zero.

## Pop your video in

`templates/pop-in/storyboard.json`. For a user with a recording the components could not recreate (a screen capture, a product clip). **Your video becomes the whole white window**: the typed prompt is the house's, then the hero composer
morphs into your 16:9 clip, rounded to the window's corners, on the ground; then the claim and the lockup. Only the text states are Cerebras'; there is no chat, no pane and no window chrome around your video. A clip that is not exactly 16:9
is shown whole with black bars (`popin.fit` overrides). Point `popin.video` at your file (any format ffmpeg reads; its frames are extracted at the film's frame rate and fitted to 1608 x 905). No clip handy? `bash templates/pop-in/make-sample-clip.sh` writes a stand-in.

```bash
python3 tools/make-film.py templates/project-demo/storyboard.json --still
```

## Rules for someone else's agent

1. Change words and the theme; do not edit `components/agent/*` to change a film. A new look is a new theme (tokens in `agent.css`); a new part is a new component; ask the owner first.
2. Never invent colours, weights or colour combinations; every theme reuses the existing ones.
3. A kit holds only a model's branding (`kits/<kit>/brand/`); the house marks are `brand/cerebras/`. Do not copy someone else's logo into the repo without the owner's say.
4. Check your work by looking: `--png-at` a moment in each scene, or `--contact`. A film that fails to build says why (`storyboard refused: ...`).
5. Cloud rendering: `node tools/agent-film.mjs film.html --engine lambda` (needs the function deployed with `bash lambda/deploy.sh` and AWS credentials in the environment). A pop-in film also needs `tar` and the `aws` CLI: its frames are staged in the deploy bucket. It is no faster than local for a 20 s film (measured about 2 minutes either way); it saves needing Chrome and ffmpeg on your machine.

## What is not here yet

Transitions other than a crossfade, audio, the video-specific pages (the review pages rebuild each reference video frame by frame; this template is the generic version), and cloud rendering.


## Long films: threads, streaming, scrolling, and the four examples

A 40-60 s film is made by letting the agents talk and the demo move, not by holding a still. A `thread` scene is `{"scene":"thread","ms":N,"thread":[{"kind":"say","who":"Researcher","text":"..."},{"kind":"tool","text":"Opened docs"},{"kind":"user","text":"..."}]}`:
each message starts after the last has finished streaming (tokens / `tps`, at least 1,000 a second) plus a pause, a message not yet begun is not drawn, and the view scrolls to keep the newest in sight. Any scene may override `prompt`, `tool`, `meter`, `answer`, `claim`,
`tps` for itself; `answer.stream_ms` makes the answer stream in; a `popin` scene's `clip_from` (ms) starts your clip part-way, so one clip can serve two scenes. Four ready storyboards are in `templates/examples/`
(`research-duet`, `browse-and-report`, `code-review-crew`, `ops-triage`, 43-45 s each), with brand-free stand-in clips from `node tools/standin-clip.mjs` (`out/standin/`). Build one with `python3 artifact/agent_film.py templates/examples/research-duet.json`.

## Speed is the point: 1,000 tokens a second and side by side

The film demonstrates Cerebras speed, so streaming obeys it in code: `MIN_TPS = 1000`. A `thread` streams at `tps` (default 1000) and the loader refuses less; `answer.stream_ms` may not imply fewer than 1,000 tokens a second (tokens are estimated as four thirds of the words, the same estimate for every lane). So text at Cerebras speed arrives in a few frames: **write more text, not slower text**, and fill time with the demo moving (a pop-in clip) and with a `versus` scene, where the slow lane takes the time. A `versus` scene needs `gpu_tps`, `cerebras_tps` (1,500 by default) and a `note`; `tools/agent-film-verify.mjs` check 12 holds the Cerebras lane at or over 1,000, finishing first, with every token counted and Done showing.

The `versus` lanes are the comparison layout's components (Cerebras's own comparison video), adjusted for the agent window: Cerebras on the left with the accent title and clock pill; the DONE card with the original's overshoot drop-in and colours (tinted for the winner, grey for the loser) that STAYS up once it has arrived; the winner's confetti (the same seeded burst); and the competitor lane DESATURATED (grey marks, chips, bubble, accent). Both DONE cards are held at least 3 s (`DONE_HOLD_MS`; the loader refuses a shorter scene), and `tools/agent-film-verify.mjs` check 12 holds all of it.

**Components are progressive, never pre-sized.** Anything an LLM would render word by word is built that way: `[data-appear]` (a message, a bullet *with its marker*, a footer) takes NO room until it begins, a streamed word takes none until it is rendered (`.rv-off`, set by film.js from the time), so a box is one line tall at its first word and grows with its text, and the thread follows the newest rendered word. Never write a component that is drawn at full size with its text arriving afterwards. `tools/agent-film-verify.mjs` check 13 holds it (zero room before it begins, short at the first word, never shrinks). At 1,000+ tokens a second the build is only a few frames long, so write enough text for it to be seen.

**The maths on screen is exact** (check 15). A `versus` lane has no pauses: its time is `tokens / tokens-a-second` to the millisecond, the live token count is `tps x time`, the words rendered follow the tokens (tokens are four thirds of the words), the DONE pill reads that time (two decimals), and the two lanes' times are in the ratio of their rates. So 1,000 against 50 tokens/s reads 0.31 s against 6.12 s: 20 times, because the same 306 tokens take 20 times longer. A lane that is only a few times apart on screen would mean the text was too short or a pause had been counted in, and the check fails it.

**Transitions are contracts** (check 14): in a morph the target's contents (the title bar with its three lights first) stay invisible until the card has landed on the target's rectangle (the last 20% of the morph is their fade-in); the DONE cards are fully up until the crossfade out begins and gone 150 ms into it; the GPU lane never carries the Cerebras mark (check 12).


## What every theme does without being asked, and what is optional

**Always (no key, the same in every theme, held by `tools/agent-film-verify.mjs` checks 14 and 16):** the typing scene ends with the mouse: the send button is the disabled grey until the first character, then the accent; after the last character the pointer glides in from below (700 ms), is on the button at the click, which presses (0.86 for 140 ms); the caret stops; the composer then morphs (tilting in perspective as it grows) into the next scene. "Preparing this turn" ticks (1s, 2s ...). A typing scene must therefore be at least 2,000 ms.

**Optional (absent = nothing is drawn):** `attachment`, `timer`, `answer.confetti`, `versus.fast_forward` (the slow lane runs N times faster from 0.8 s after the fast lane is done, with the source's `>> 5X` badge; both lanes' maths stay exact because the slow lane follows its own clock), message `title` (a section title streamed first) and `verdict` (the source's verdict card with its accent rule and FINAL ANSWER tag; the accent is grey in the competitor lane), scene `cut: true` (a hard cut into the scene, as reference video 1 does into the claim), `lockup.variant: "powered-by"`, `ground` scenes, and the `ask`, `second-turn`, `integration` and `browse` states. A thinking row (the next section's title and three pulsing dots) shows before a message wherever there is time for one. Each `versus` lane also carries the source's follow-up composer, whose model chip reads ANALYZING while the lane works and READY when it is done, and the labels `Cerebras (WSE)` and `GPU Inference` (`versus.cerebras_label`, `versus.gpu_label`). `templates/examples/states-tour.json` uses every state in one film.

**Every theme, one storyboard.** `templates/examples/states-tour.json` plays unchanged in all six themes (only `theme` differs), built, measured, verified (about 700 checks each) and cloud-rendered:  Two theme-specific facts: the competitor lane is desaturated by a filter over the whole lane (never theme-specific greys, which were unreadable on the dark `ember` window); and the canvas-ground themes (`glow`, `bloom`, `tile`) render slowly and make large windows, so render them in more windows: `--segments 16` to 20 (a tile window of 7 s exceeded the Lambda's 6 MB response limit, a glow one timed out at 300 s).


## Rules you must follow (each is held by a check or a refusal; `tools/make-film.py` applies the render ones for you)

**Content**
1. Every word is yours or the user's; never invent a feature, number, customer or quote. A browse page is a generic stand-in; never a real company's page, logo or a person's private data.
2. Colours and weights are not keys: pick a `theme`, change words and logos only. Never put the Cerebras mark on a competitor; the competitor lane is desaturated by the system.
3. Honest speeds: Cerebras streams at least 1,000 tokens a second (refused below it), and **Kimi is stated as up to 1,000 tokens a second**: a film whose `model` is Kimi never claims, streams or shows a Cerebras lane above 1,000 (refused: `MODEL_UP_TO` in `artifact/agent_film.py`), so a Kimi film runs at exactly 1,000; another model has no cap until one is stated there; a GPU rate needs a `note` (its source, or that it is illustrative); a claim's number has a footnote; never raise a number to make a film read better.
4. An `intro` slide opens a film that is not a rebuild; the typed prompt (`typing`) opens a rebuild or a run where the prompt is the story. A typing scene is at least 2,000 ms, an intro holds at least 2.2 s after it builds, both DONE cards of a `versus` hold 3 s, a `popin` clip is 16:9 (else cropped).
5. Fit: the typed prompt at most about four lines (430 px), an answer must end above the docked composer, an intro is a title and a description. The build MEASURES the layout in a real Chrome and refuses what does not fit; shorten the text, never loosen the check.

**Render**
6. Never render a film that has not passed `node tools/agent-film-verify.mjs film.html` (`0 failed`). `tools/make-film.py` stops before the render if it fails.
7. Look at a still (`--png-at`, or `make-film.py --still`) before you render.
8. Cloud rendering shares ONE account limit on concurrent windows: render one or two films at a time (a window that hits the limit is waited out and retried, up to 12 times, and each film sends at most 24 windows at once: `--max-parallel N`); ten films at once starve each other. Cloud windows: **16 windows (`--segments 16`) for any film with a pop-in clip and for the `glow`, `bloom` and `tile` themes; 8 otherwise.** A busy window is larger than the function's 6 MB reply limit, a textured ground is slow (a glow window timed out at 300 s with 8). `make-film.py --cloud` chooses for you. Render the slow-ground themes one at a time when verifying (three Chromes at once time out: that is the load, not the film).
9. A new template or state goes into the gate (`tools/agent-film-check.sh`) in the same change, with a staged refusal.

**Themes** (pictures in `templates/themes/`, rebuilt by `python3 tools/agent-film-theme-gallery.py`): `halftone` (default, fastest), `paper`, `ember` (dark), `glow`, `bloom`, `tile` (the last three are slow-ground themes). In `tile` the claim line is the theme's orange on gold: the reference's own look and weak in contrast; keep the claim short.


## What a hackathon team will bring, and what the film does with it

The API is built so that the usual material works and the unusual is refused with a reason, never a crash (`python3 tools/agent-film-fuzz.py`: 500+ malformed inputs, all accepted or refused cleanly; `python3 tools/agent-film-fuzz-build.py`: awkward valid inputs built in a real browser).

| They bring | What happens |
|---|---|
| a screen recording (mp4, mov, webm; any size; with audio) | the audio is dropped (the film is silent); a clip within 3% of 16:9 fills the window, **any other shape (a 16:10 laptop recording, a phone's 9:16, a 4:3 screen) is shown whole with black bars**, never cropped (`popin.fit`: `auto`, `cover` or `contain` to override) |
| a long recording (minutes) | take the part you want with `clip_from` (ms into the clip) and the scene's `ms`; only that stretch is extracted (at most 120 s of clip per film, and a scene shows at most 60 s). Untrimmed, the scene uses the first 60 s |
| an agent's chat log (OpenAI `role/content/tool_calls`, Anthropic content blocks) | put it in `messages` as it is: the first user message is the prompt, an assistant message is said by `name` (else the project), a tool call or result is a tool line, a system message is dropped |
| a logo | `intro.logo` takes SVG, PNG, JPG or WebP; `partner_logo` (the closing lockup) takes SVG |
| text in another language, emoji, right-to-left text | rendered (the house faces plus the system's fallbacks); keep it short; a very long word wraps instead of overflowing |
| text that is too long | refused with its length and the limit: title 80 characters, intro description 320, model 60, prompt 400, a message 1,200, an answer lead 200, a bullet 400, 300 messages, 12 bullets; the measure pass also refuses an intro that does not end by y=1010 and a claim line too wide for the slide |
| a transcript with a key or a token in it | **refused**: text that looks like an API key, a cloud or GitHub or Slack token, a bearer token or a private key stops the build (a film is published). Emails, names and customers' data are not detected: scrub them yourself |
| HTML or code in a text | shown as text, never executed |
| a model that is not Kimi | allowed; the 1,000 tokens a second floor still applies, and there is no cap until one is stated in `MODEL_UP_TO` |
| no GPU number | ask; or the 50 tokens/s illustration with its note, and say so |

**Other points a team will ask:** a film may end on any scene (the lockup is the usual end); there is no minimum length beyond what each scene needs; a "10x faster than X" claim is not a claim the film makes: use `compare` with the two rates and it shows the exact ratio on screen (a rate you measured or a stated illustration); a model that is not Kimi has no stated speed in this kit, so the claim scene needs `claim.number` and a side-by-side needs `cerebras_tps`, both the rates YOU measured (the 1,000 tokens a second floor still applies); the closing lockup is Cerebras beside `partner_logo` (Kimi's by default for a Kimi film; for any other model with no `partner_logo`, the Cerebras logo alone: no other model's logo is in this kit); the film is silent, so music and narration are added afterwards, outside this kit.

**Fixed words in a lane or the claim** can be set in your language with `words`; the lane titles are `versus.cerebras_label` and `versus.gpu_label` (in a run log, put them inside `compare`: `"gpu_label": "GPU"`). Verified on a Spanish film (`words` for the DONE card, the follow-up box, the answer footer, the claim's "Up to", the final-answer tag).
