# CLAUDE.md

Guidance for AI coding agents (Claude Code, OpenClaw and similar) working in this repo.

This repo is an **optional demo video starter kit** for the **Cerebras × Kimi K3.1 Pro × OpenClaw Hackathon**. It gives participants Cerebras styling, branding, elements and fonts, a worked example demo, and a post template. Participants clone it and ask their agent to adapt it to their own project.

## Source of truth

The official [Hackathon Guide](https://docs.google.com/document/d/1Vvf2SjScBt3yBeTVZRoKtOyE7rGEP-gWV_ApzwXepEQ) wins over anything in this repo. If the two disagree, follow the guide and update the repo to match.

## Current event facts

Use these values everywhere in the repo (README, config, templates, example copy).

| Item | Value |
| --- | --- |
| Event | Cerebras × Kimi K3.1 Pro × OpenClaw Weekend Hackathon |
| Hacking window | Sat Nov 21, 10:00 AM PT to Sun Nov 22, 10:00 AM PT (24 hours) |
| Submission deadline | Sun Nov 22, 10:00 AM PT |
| Judging tally | Tue Nov 24, 10:00 AM PT |
| Model ID | `moonshotai-kimi-k3.1-pro-trial` |
| Base URL | `https://api.cerebras.ai/v1` (standard Cerebras Inference API) |
| Reasoning | Off by default; set `reasoning_effort` to enable it |
| Harness | OpenClaw (required for all projects) |
| Hashtag | `#KimiOnCerebras` |
| Tags on X | `@Cerebras` and `@Kimi_Moonshot` |
| Reddit | [r/cerebras](https://www.reddit.com/r/cerebras), flair `Kimi K3.1 Pro Hackathon` |
| Support | [Cerebras Discord](https://discord.gg/XWXRquhx7H), `#hackathon-support` |

### Prizes

- **Audience Choice on X:** 3 × $1,000 for the most organic impressions on the X demo post
- **Audience Choice on Reddit:** 1 × $1,000 for the most organic upvotes on r/cerebras
- **Speed Bounty, Santa's Speedy Shopper:** $1,000 for the fastest run (tokens per second) of a holiday task: use OpenClaw with Kimi K3.1 Pro on Cerebras to find 5 real Christmas gifts from real shopping websites. Entry steps are in the guide.

### Submission

1. **Required:** post the demo video on X with the project description, tagging `@Cerebras` and `@Kimi_Moonshot` and including `#KimiOnCerebras`.
2. **Optional:** also post on r/cerebras with the `Kimi K3.1 Pro Hackathon` flair to compete for the Reddit prize.

Main project submissions go on X (required) and Reddit (optional). Speed Bounty entries are posted in #share-your-demo on Discord.

Each post should include: Project Name, Team Members, Project Description (2–4 sentences), Demo Video, GitHub Repository (recommended).

## Video rules

- **Maximum 60 seconds.** Hard limit.
- **Show Cerebras speed:** make it clear how fast inference improves the experience.
- **Side-by-side vs a GPU-based provider:** recommended, not required.
- **Focus on the project:** key features, workflow and impact.
- **Privacy:** no API keys, emails, notifications, credentials or personal browser tabs on screen.
- **Record public X and Reddit demos with standard OpenClaw.** The OpenClaw speed patch is only for Speed Bounty entries.

The kit is optional inspiration. Never present its style as required.

## Self-check (run when asked to "check the repo", and before any release)

Search the whole repo (README, docs, config, templates, example scripts, captions, on-screen text) and fix anything that conflicts with the facts above. In particular, look for:

- [ ] "TPS Bounty", "bounty hunt" or "fastest TPS prompt" → replace with the **Speed Bounty (Santa's Speedy Shopper)** wording
- [ ] Any instruction to submit a main project in Discord or in "track channels" → remove; main project submissions are X (required) plus Reddit (optional). Only Speed Bounty entries are posted in #share-your-demo on Discord
- [ ] Wrong or vague dates ("Tuesday morning", "Sunday, Nov 21", "Monday, Sunday") → use the dates in the table
- [ ] Any model ID other than `moonshotai-kimi-k3.1-pro-trial`, or a non-standard endpoint
- [ ] Video length over 60 seconds, or the GPU comparison described as mandatory
- [ ] The kit described as required rather than optional
- [ ] Post templates missing `@Cerebras`, `@Kimi_Moonshot` or `#KimiOnCerebras`
- [ ] Hard-coded API keys, tokens, Org IDs or personal details anywhere, including git history of example files
- [ ] Any mention of the OpenClaw speed patch outside the Speed Bounty context, or any use of it in example demo footage for public X/Reddit posts
- [ ] Broken links (guide, Discord invite, subreddit, examples page)

Report what you changed as a short list, and flag anything you could not verify instead of guessing.

## Updating config

When adapting the kit to a participant's project, or when event details change:

1. Keep event values in **one place**: the repo's config file (for example `config.*`, `src/config.*` or `.env.example`). Read from config elsewhere; don't copy values into individual scenes or templates.
2. Put secrets only in a local `.env` that is git-ignored. Commit an `.env.example` with placeholder values such as `CEREBRAS_API_KEY=your-key-here`.
3. After any change, re-run the self-check above and confirm the demo still renders at 60 seconds or less.

## Hard rules

- Never commit API keys, Org IDs or other credentials.
- Only mention the OpenClaw speed patch in the context of the Speed Bounty (https://github.com/wkasekende/openclaw-speed-patch). Never use it in example demo footage for public X/Reddit posts.
- Never change Cerebras or Moonshot AI branding assets beyond what the existing kit already does.
- Don't invent event rules, prizes or dates. If something isn't in this file or the guide, ask or leave a TODO.
