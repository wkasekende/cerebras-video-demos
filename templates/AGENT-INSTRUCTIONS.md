# Instructions for an AI agent: turn the user's project into a Cerebras demo film

You are working in the Demo Kit repository. Your job: take the user's project (an agent they built) and produce an MP4 with the film template. Follow this file exactly; where it says STOP, stop and ask the user.

## Hard rules

1. **Use only what the user gives you.** Every word on screen is the user's: their project name, their description, their agent's real messages and answer. Never invent a feature, a number, a customer, a result or a quote. If something is a stand-in, the film's footnote already says "Demo shown with mock data".
2. **Only the closed API.** You write JSON (a storyboard or a run log). You do not edit `artifact/`, `components/`, `tools/`, CSS or colours. If the API cannot express what the user wants, tell them what is missing; do not work around it.
3. **Never render before it verifies.** `tools/make-film.py` enforces it; do not use `--no-verify` for a final film.
4. **Honest Cerebras numbers.** `cerebras_tps` is at least 1,000 (the loader refuses less). If you add a GPU lane, `gpu_tps` is a number the user gave you or a stated illustration, and `note` says which. Never raise a number to make the film look better.
5. **Values you were not given are not yours to keep.** The templates carry stand-in values (a GPU rate of 50, a model version, a claim number, a sample answer). Ask the user, or leave the key out, and **list in your final report every value you assumed**. The answer's footer numbers are derived from the run: leave them out.
6. **No real third-party material you were not given.** Browse pages in the `browse` state are generic stand-ins; never put a real company's logo, page or a person's private data in a film.
7. **When a command refuses, read the message, fix the JSON key it names, run again.** Do not retry unchanged; do not loosen a check.

## Step 0. Check the environment

```bash
npm install
python3 tools/make-film.py --check     # seconds; must print READY. If it prints NOT READY, tell the user what it lists and stop
```
(`bash tools/agent-film-check.sh` is the full gate for people changing the repo: minutes, not needed to make a film.)

## Step 1. Ask the user (all at once, with the defaults)

1. What is the project called? (`title`/`project`)
2. In a sentence or two, what is the agent and what does it do, and for whom? (`description`: the intro slide is a title and a description, no bullet points)
3. (skip: there are no points; do not ask for bullet points)
4. Which model does it run on? (`model`: write it as the user said it; if they say only "Kimi", write `Kimi`, never add a version. Kimi is stated as up to 2,000 tokens a second, so a Kimi film runs at exactly 2,000)
5. What task would a user type to it? (`prompt`; keep it to two or three lines)
6. **What do they have: a screen recording, or a text record of a real run?**
   - Recording → Path 1 (put a video inside). Ask for the file path (any shape: a non-16:9 recording is shown whole with black bars).
   - A run (the agent's messages, tool calls, final answer) → Path 2 (recreate it as HTML). Ask for those, in order.
   - Neither → ask them to run the agent once and paste its transcript, or to record the screen.
7. Which look? Dark: `ember` (fast) or `bloom` (cinematic, slow ground). Light: `paper` (quiet) or `glow` (warm grain, slow ground). Colourful: `halftone` (the default, fast) or `tile` (gold, slow ground). Show them `templates/themes/*.png` or `templates/START-HERE.md` section 2 and ask; if they only named a mood, map it as above and say which you chose. Slow-ground themes need `--cloud` for the final render.
8. Optional: a file the user attached (`attachment`), an elapsed-time pill (`timer`), GPU against Cerebras (`compare`). For the GPU ask: "What GPU speed in tokens a second should I compare against, and where does it come from?" If the user has none, use `"gpu_tps": 50` with the note `Illustrative rates: a typical GPU-served speed against Cerebras. Same text, same token estimate.` and **tell the user in your report that the GPU rate is an illustration, not a measurement**.

## Step 2a. Path 1: put a video inside

```bash
cp templates/project-demo/storyboard.json my-film.json
```
Edit only: `slug` (lowercase letters, digits, dashes), `model`, `theme`, `popin.video` (the path to the user's real recording), `claim.footnote`, and `scenes[0].intro` (`title` and `description` only; `logo` is an SVG, PNG, JPG or WebP path, optional). Do NOT type any `ms`: every scene's length is derived (the clip's own length, the time the intro needs to be read), and there is no `prompt` in this template (nothing types it). `claim.footnote` says what the number is, for example `*Up to 2,000 tokens per second: Kimi on Cerebras.`; keep `*Demo shown with mock data.` only if the data on screen really is mock.

**If the user asks for something the template cannot do:** bullet points or a feature list on the opening slide are not allowed (the intro is a title and a description: fold the features into the description sentence and tell the user); a claim above the model's stated speed is refused (say so; for Kimi it is up to 2,000); a film cannot be padded to an exact length (its length is its content: say so, and if they want it longer they need a longer clip); the closing lockup is Cerebras with the model's logo (Kimi by default), not the user's product; use `partner_logo` only for a logo the user owns or has the right to use.

**Requests the film cannot do** (say so to the user, name the closest thing it can do, and never edit components, themes or CSS to work around it): a different intro style or animation (the intro is the house one: a title and a description), bullet lists or extra slides, your own colours or fonts, audio or narration, an exact length, a claim above the model's stated speed, a comparative multiple such as \"10x faster than GPT-4o\" (the film shows an exact ratio from two rates via `compare`; it does not state a multiple of a model you have no rate for), music or narration (the film is silent: tell the user to add sound after the render). For a mood word, map it to a theme: dramatic or cinematic means `bloom` (dark, slow ground), clean or quiet means `paper`, colourful means `halftone` or `tile`, dark means `ember` or `bloom`.

**If you cannot ask the user** (you are working alone), use the defaults, and end your report with a list of every value you assumed.

## Step 2b. Path 2: recreate it from a run

```bash
cp templates/from-run/run.json my-run.json
```
Fill it with the user's real material:
```json
{"project": "...", "description": "...", "model": "...", "theme": "halftone",
 "prompt": "the task as typed",
 "messages": [
   {"who": "Agent name", "title": "optional section title", "text": "what it said, verbatim"},
   {"kind": "tool", "text": "Searched the order system · what it found"},
   {"who": "Writer", "verdict": true, "title": "Reply drafted", "text": "the final message"}],
 "answer": {"lead": "one line", "bullets": [["Bold run-in:", "the rest"]]},
 "compare": {"gpu_tps": 60, "gpu_tps_range": [30, 99], "note": "where this number comes from"}}
```
Rules and the meaning of every key are in [`from-run/README.md`](from-run/README.md) (read it before you fill the file). In short: required are `project`, `description`, `model`, `prompt`, `messages`, `answer.lead`; a *said* message needs `who` (for a single agent, its own name every time); what the agent *did* (read, searched) is a `kind: tool` line; `verdict: true` only on the last said message (the full final text), and `answer` is the short recap card; leave `footer_seconds` and `footer_tokens` out; `compare` is optional and needs a `note`; keep the answer short enough to fit; no message may be empty.

## What users bring, and what to do with it

- **A recording in any shape or length:** point `popin.video` at it; a 16:10 or phone recording is shown whole with black bars; for a long one set the scene's `clip_from` (ms into the clip) and `ms` to take the part that matters (at most 60 s per scene). The sound is dropped: tell the user.
- **A chat log from a framework** (OpenAI or Anthropic format): put the list straight into `messages`; do not retype it.
- **A logo:** SVG, PNG, JPG or WebP in `intro.logo`.
- **Secrets and personal data:** the build refuses text that looks like an API key or token. Emails, names and customer data are NOT detected: read what you are putting in and remove personal data (replace it with `...`) before you build, and tell the user you did.
- **A language other than English:** write all the user's text in their language; the few fixed words the film draws ("Up to", "DONE", "Ask a follow-up", "Worked for N seconds" ...) stay English unless you set the optional `words` key (see `agent-film/README.md`); numbers stay in the 1,000 style.
- **The user's own logo for the closing slide:** `partner_logo` shows it beside the Cerebras logo (it replaces Kimi's); SVG, PNG, JPG or WebP; check it reads on the theme's ground (a dark logo on a dark theme does not).
- **A model that is not Kimi:** the kit has no stated speed for it, so a claim scene needs `claim.number` and a side-by-side needs `compare.cerebras_tps`: ask the user for the rates they measured (the 1,000 floor applies). Never put a speed the user did not give you.
- **Too much text:** the build refuses with the length and the limit; shorten, do not split a sentence across messages to dodge it.

## Step 3. Preview, show the user, then render

```bash
python3 tools/make-film.py <my-film.json | my-run.json> --theme <theme> --still      # builds, measures, verifies, photographs ONE frame
```
The command prints the film's length and where each scene starts, then photographs the **money shot** by default (the moment both DONE cards are up in a side-by-side film, a little way into the clip for a recording, else the middle of the second scene); `--at MS` photographs any moment (use the scene starts it printed). Open the PNG it prints and look at it. Check the text is the user's, nothing is cut off, and the theme reads well. **Show the user the still and ask before rendering.** Then:
```bash
python3 tools/make-film.py <same input> --theme <theme>            # renders the MP4 locally (about 1.5 minutes per 20 s of film)
python3 tools/make-film.py <same input> --theme <theme> --cloud    # on the AWS function, if the user has set it up
```
The command picks the number of cloud windows itself (16 for a recording or for `glow`, `bloom`, `tile`, else 8; a busy window is larger than the function's 6 MB reply limit).

## Step 4. Report

Tell the user the MP4's path (`out/agent-film/<slug>/<slug>.mp4`), its length, the theme, and exactly which words were theirs. If anything is a stand-in (a sample clip, a placeholder number), say so.

## When a command stops (fix the JSON key it names)

| Message | Fix |
|---|---|
| `unknown key(s)` | remove or rename the key; the message lists the allowed ones |
| `theme ... is not one of` | one of `halftone paper ember glow bloom tile` |
| `typing scene needs at least` / `intro slide needs at least` | `ms` too small; in Path 2 the converter derives it, so check the text you gave |
| `answer card ends ... px into the docked composer` | shorten `answer` (fewer or shorter bullets) |
| `typed prompt is ... px tall` | shorten `prompt` |
| `versus needs a "note"` | add `compare.note` |
| `cerebras_tps ... at least 1000` | remove `cerebras_tps` or set it to 1,000 or more |
| `popin video not found` | fix the path |
| `a thread scene needs` / `message ... text is empty` | every message needs words; every `say` needs `who` |
| `STOPPED at the verify` | a deterministic check failed: do not render; report the failing line to the user |

## Never

Never edit components, themes or CSS; never add a colour or weight; never put the Cerebras mark on a competitor; never claim a speed the user did not give you; never render with `--no-verify`; never skip showing the still.
