# The run log (`run.json`): what to put in each key

A run log is what your agent did, written down. `python3 tools/make-film.py run.json --theme <theme> --still` turns it into a film; every duration is derived from your words, so you never type a time. Start from [`run.json`](run.json) in this folder.

| Key | Required? | What to put |
|---|---|---|
| `project` | yes | the agent's name, as it should read as the slide title |
| `description` | yes | what the agent is and does, and for whom, in a sentence or two (no bullet points) |
| `model` | yes | the model's name as the user said it. If they only said "Kimi", write `Kimi`: do not add a version they did not give you |
| `prompt` | yes | the task the user typed, in their words (two or three lines at most) |
| `messages` | yes | what the agent said and did, in order (see below) |
| `answer` | yes | the short result card shown at the end (see below) |
| `theme` | no | `halftone` (default), `paper`, `ember`, `glow`, `bloom`, `tile`; or pass `--theme` |
| `claim` | no for Kimi; **`number` required for any other model** | `{"number": 1000, "unit": "tokens per second", "footnote": "*Up to 1,000 tokens per second: Kimi on Cerebras."}`. For Kimi the number may not exceed 1,000 (it is stated as up to 1,000). The footnote says what the number is; the default `*Demo shown with mock data.` is only for mock data |
| `compare` | no | `{"gpu_tps": 60, "gpu_tps_range": [30, 99], "note": "where the GPU rate comes from"}`: show the run against a GPU, side by side. `note` is required with it. Optional inside: `cerebras_tps` (1,000 for Kimi), `fast_forward` (5 gives the `>> 5X` badge) |
| `attachment` | no | `{"title": "Billing export", "meta": "CSV · 41,820 rows"}`: a file the user attached |
| `timer` | no | `true`: an elapsed-time pill in the title bar |
| `partner_logo` | no | your logo for the closing slide, beside the Cerebras logo (replaces Kimi's): SVG, PNG, JPG or WebP |
| `words` | no | the film's fixed words in your language (see `templates/agent-film/README.md`, key `words`) |
| `slug` | no | the output folder's name (default: made from `project`) |

**`messages`** are played in order. Two kinds:
- `{"who": "Name", "title": "optional section title", "text": "what it said, verbatim"}`: something the agent **said**. `who` is the speaker. For a single agent use its own name for every message (do not invent roles); for a team of agents, each agent's name.
- `{"kind": "tool", "text": "Searched the order system · what it found"}`: something the agent **did** (read, searched, called). One line.
- `title` is optional: a short section heading shown above the message's text (and in the "thinking" row just before it). Use it for a step's name ("Reading the ticket"); leave it out if the user did not give one: do not invent titles.
- `"verdict": true` on the LAST said message marks it as the final answer (a card with the accent rule and a FINAL ANSWER tag). It is the agent's full final text; the `answer` below is the short recap.

**A chat log from a framework works as it is.** If you already have the agent's messages in OpenAI format (`role`, `content`, `tool_calls`) or Anthropic format (content blocks with `text`, `tool_use`, `tool_result`), put that list in `messages` unchanged: the first user message becomes the `prompt`, an assistant message is *said* by its `name` (else the project's name), a tool call or result becomes a tool line, a system message is dropped. Remove keys, tokens and personal data first (the build refuses what looks like a key).

**`answer`**: `{"lead": "one line result", "bullets": [["Bold run-in:", "the rest"], ...]}`. Keep it short enough to fit above the composer (the build refuses one that does not). The answer's footer ("Worked for N seconds", "Done in N seconds · N output tokens") is **derived from the run**: leave `footer_seconds` and `footer_tokens` out; do not copy numbers from the template.

**A run log always opens with the intro slide and then the typed task** (the film is intro, the user typing the task and clicking send, the run, the answer, the claim, the lockup); there is no choice to make.

**`compare` and a slow GPU.** The GPU lane runs for as long as its tokens need at its rate (a 360-token run at 30 tokens/s takes 12 s), and the scene is as long as that. Add `"fast_forward": 5` inside `compare` to run the slow lane 5 times faster from 0.8 s after Cerebras is done (with the `>> 5X` badge); use it when the GPU lane would take more than about 10 s. The maths on screen stays exact either way.

**Everything on screen is the user's.** Do not keep template values you were not given (a GPU rate, a version, a number): ask, or leave the key out, and say in your report which ones you assumed.

**Length.** The film is the intro (about 3 s), the typed task (about 4 s), the run (the Cerebras lane takes a fraction of a second; a GPU comparison runs as long as the GPU lane would), the answer (6.5 s), the claim (3.5 s) and the lockup (3 s): a short run comes out near 25 s, which is right for a short demo.

**The GPU baseline for Kimi K3.1 Pro.** On OpenRouter the model's providers run at about 30 tokens a second (Moonshot's own API) to 99 (Amazon Bedrock), checked November 2026; it moves, so open the model's page before you publish. The shipped films use `"gpu_tps": 60` (a point inside the range, not a measured median) and `"gpu_tps_range": [30, 99]`: the lane streams at 60 and prints the range beside it, and the claim is "up to 16x" (1,000 against 60). Use your own measured number if you have one, and cite where it comes from in `note`. Against the fastest provider the ratio is about 10x, against the slowest about 33x.
