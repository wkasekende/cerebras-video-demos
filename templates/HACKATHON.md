# Hackathon guide: make a Cerebras-styled demo film

> **Start with [`START-HERE.md`](START-HERE.md)**: two paths (a recording, or your agent's run), six themes, one command. An AI agent doing it for you: [`AGENT-INSTRUCTIONS.md`](AGENT-INSTRUCTIONS.md)..

## The event: Cerebras x Kimi K3.1 Pro x OpenClaw Weekend Hackathon

This kit is **optional**: a starting point and reference for presenting your demo video (Cerebras styling, branding, elements and fonts, a worked example and a post template). You do not have to use it, and its style is not required. The official [Hackathon Guide](https://docs.google.com/document/d/1Vvf2SjScBt3yBeTVZRoKtOyE7rGEP-gWV_ApzwXepEQ) wins over anything here. What the event asks, and what the kit does about it:

| The event says | What the kit does |
|---|---|
| Demo video **60 seconds at most** (hard limit) | `make-film.py` prints the film's length and warns above 60 s. Keep your scenes short: an intro is about 6 s, the clip 20 to 35 s, the claim and lockup about 8 s |
| **Show Cerebras speed** | the claim card, the live tokens-per-second meter and the DONE clocks are derived from your numbers; Kimi on Cerebras is stated as up to 1,000 tokens a second |
| **Side-by-side with a GPU provider** recommended | the `versus` scene (Cerebras on the left, a desaturated GPU lane on the right; set `compare` in a run log) |
| **Focus on your project** | the intro slide is your title and description; your own recording is the whole window |
| **Protect your privacy** (no notifications, tabs, keys, emails) | the build refuses a storyboard that contains something shaped like an API key; you still have to look at your own recording |
| Tag **@Cerebras** and **@Kimi_Moonshot**, add **#KimiOnCerebras** | in your post, not the video |
| Must use **Kimi K3.1 Pro on Cerebras** and the **OpenClaw** harness | your project does; the film's `model` field should say so (model ID `moonshotai-kimi-k3.1-pro-trial` on the standard Cerebras Inference API, base URL `https://api.cerebras.ai/v1`; reasoning is off unless you set `reasoning_effort`) |

**Timeline** (Pacific Time): hacking window Sat Nov 21, 10:00 AM PT to Sun Nov 22, 10:00 AM PT (24 hours); submissions due Sun Nov 22, 10:00 AM PT; X impressions and Reddit upvotes are counted Tue Nov 24, 10:00 AM PT.

**Prizes:** Audience Choice on X, 3 x $1,000 (most organic impressions on the X demo post); Audience Choice on Reddit, 1 x $1,000 (most organic upvotes on [r/cerebras](https://www.reddit.com/r/cerebras), flair "Kimi K3.1 Pro Hackathon"); Speed Bounty "Santa's Speedy Shopper", $1,000 for the fastest run (tokens per second) of a holiday task, with OpenClaw and Kimi K3.1 Pro on Cerebras finding 5 real Christmas gifts on real shopping websites. The Speed Bounty entry steps are in the guide. Organic reach only. Record your public X and Reddit demos with standard OpenClaw.

**How to submit:** post your demo video on **X** (required) with `@Cerebras`, `@Kimi_Moonshot` and `#KimiOnCerebras`; optionally also post on **r/cerebras** with the flair above. There is no Discord submission: Discord is for questions and support.

**The post** (X is the official submission; Reddit is optional):

```
Project Name: <name>
Team Members: <X / Reddit handles>
Project Description: <2 to 4 sentences: what it does, for whom, what the speed changes>
GitHub Repository: <link, recommended>
Demo Video: (attached, 60 s max)
#KimiOnCerebras @Cerebras @Kimi_Moonshot
```

**Fastest route to a good entry:** build your project with OpenClaw on Kimi; screen-record it working; Track A below (15 minutes) for the film, or Track C (`from-run`) if your agent's run log is the story; post the MP4. Questions and support: the [Cerebras Discord](https://discord.gg/XWXRquhx7H), `#hackathon-support`.

Two tracks. **Track A: pop your own recording in** (about 15 minutes: edit one JSON file; `templates/project-demo/`). **Track C: from your agent's run** (no recording needed): write `templates/from-run/run.json` (project, description, the task, what the agent said and did, the answer) and run `python3 tools/make-film.py templates/from-run/run.json`. Which one? See [`templates/agent-film/README.md`](agent-film/README.md), "Start here".

## Before you start 

You need `python3` (3.8+), `node` (18+), `ffmpeg` and `ffprobe` on your PATH, and `npm install` run once in the repo (it fetches puppeteer and a Chrome for Testing). Check it works:

```bash
python3 tools/make-film.py --check   # seconds: prints READY
```

If that fails, fix it first: nothing below will work. The rules that apply to everything: **change words, the theme and your logo; do not change colours, weights or components.** Pick one of the six existing themes (`glow`, `ember`, `paper`, `halftone`, `bloom`, `tile`).

## Track A: Pop it in

1. **Prepare your clip.** Any format ffmpeg reads, any shape and length (the sound is dropped). A 16:9 screen recording fills the window; any other shape (a 16:10 laptop, a phone's 9:16, a 4:3 screen) is shown whole with black bars; a long recording is trimmed with `clip_from` and the scene's `ms`. No video yet? `bash templates/pop-in/make-sample-clip.sh` makes a stand-in.
2. **Copy the storyboard.** `cp templates/project-demo/storyboard.json my-film.json` (the Track A template: an intro slide, your clip, the claim, the lockup; `templates/pop-in/` is the older sample-clip template) and edit:
   - `slug`: your film's name (lowercase, digits, dashes).
   - `model`: your model's name as it should read.
   - `popin.video`: the path to your clip: a path to your recording (an absolute path is fine). It becomes the whole white window: there is no chat or browser around it.
   - `meter` and `claim`: **use numbers you measured**, not numbers you want. The claim is a promise; if you did not measure it, say "mock data" in the footnote (the template's default does).
   - `partner_logo`: your logo for the closing lockup, shown beside the Cerebras logo (it replaces Kimi's logo there). SVG with shapes filled `black` (they turn white where the theme calls for it; start from `templates/agent-film/partner-logo.svg`), or a PNG, JPG or WebP that reads on the theme's ground.
   - `scenes`: the order of the scenes. Do not type `ms`: a scene's length is derived (your clip's own length, the time an intro needs); add `ms` to a `popin` scene only to take part of a long clip (with `clip_from`). The order is checked against the film's state machine (`templates/agent-film/README.md`, "The states"); a refusal lists what may follow.
3. **Look, then make it.**
   ```bash
   python3 tools/make-film.py my-film.json --theme halftone --still    # builds, measures, verifies, photographs the money shot; a refusal says exactly what is wrong
   python3 tools/make-film.py my-film.json --theme halftone            # the MP4 (add --cloud for AWS)
   ```
4. **Render fast (cloud).** If the event's organisers deployed the render function, or you did (`bash lambda/deploy.sh`, needs your own AWS account and credentials in the environment; a pop-in film also needs `tar` and the `aws` CLI because its frames are staged in S3):
   ```bash
   node tools/agent-film.mjs out/agent-film/my-film/film.html --engine lambda
   ```
   It cuts the film into windows, renders them at once and joins them without re-encoding. Measured on 2026-11-19 (a 20 s film, 7 to 12 windows): about **2 minutes**, the same as rendering locally, because each window took 35 to 120 s whatever its length. So the cloud is for **not needing Chrome and ffmpeg on your machine** and for rendering several films at once, not for speed on a short film. Local rendering works everywhere and takes about 2 minutes per 20 s.
5. **Check before you submit.** Watch the mp4 end to end. Does the typed prompt match what your clip shows? Is the claim true? Is your logo readable on the closing screen? Is there anything in your clip you may not publish (names, keys, customer data)?

If something looks wrong: the stills are the fastest loop (`--png-at <ms>` at the start of each scene). A scene that is too short is refused; a clip that is missing is refused with its path.

## What to submit

Your mp4, your storyboard (`my-film.json`) and the clip's licence or permission. Do not commit other people's videos, logos or screenshots: keep them out of the repo (the `out/` folder is ignored) unless you have the right to share them.


## Examples to copy

`templates/examples/` holds four 43-45 s agent films (agents talking in a streaming, scrolling thread, with a moving clip popped in). Copy one, change the words and the `popin.video`, and render. Run `node tools/standin-clip.mjs` first for the stand-in clips.
