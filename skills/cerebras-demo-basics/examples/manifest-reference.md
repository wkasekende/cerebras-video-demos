# Legacy basic renderer: recording and edit inputs

This is the earlier compact SBS mode with a separate DONE card. For the reference framing and step-by-step sequence, use [story-manifest-reference.md](story-manifest-reference.md) with `render_story_demo.py` instead.

The renderer uses local files and explicit timings, not model access. Copy `synthetic-demo.json` to start a real edit; replace the fixture paths, labels, prompt, evidence, and times. Set `synthetic` to `false` only for actual recordings. Resolve all relative video paths from the manifest's directory, not the shell working directory. Do not ship `manifest.resolved.json` if its absolute source paths are inappropriate for sharing.

## Runtime

Python 3.10+, Pillow, and FFmpeg with libx264 are required. Use your agent's available Python runtime. To prepare an isolated environment when necessary:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r scripts/requirements.txt
.venv/bin/python scripts/render_demo.py --manifest examples/synthetic-demo.json --output demo-output
```

An installed `ffmpeg` is used first; otherwise `imageio-ffmpeg` supplies one. `FFMPEG_BINARY` can select an explicit executable. A fresh environment may need network access to install dependencies; the ZIP does not bundle Python or FFmpeg. The supplied font files and logos are local. No model API is used and no video is uploaded.

## Required fields

| Field | Meaning |
| --- | --- |
| `schema_version` | Integer `1`. |
| `synthetic` | Explicit boolean. `true` puts a persistent test-fixture banner on every frame. |
| `audience`, `takeaway` | Who the demo serves and what viewers should learn. Project notes, not extra on-screen headings. |
| `comparison_kind` | `same_model_infrastructure` or `different_models_workflow`. The former requires identical model labels and can show the elapsed-time ratio. The latter shows the two task times without attributing the difference to infrastructure alone. Reviewers still verify the underlying models/settings. |
| `display_prompt` | Short opening text. The renderer types this from frame zero. |
| `full_prompt` | Actual shared task prompt retained for review. A shortened display prompt must preserve its meaning. For different actual prompts/configurations, record those differences in project notes and adapt the workflow before claiming equivalence. |
| `completion_boundary` | Human-agreed observable definition of completion, applied to both clips. |
| `disclosure` | On-screen text, maximum 200 characters, visible throughout. Include setup and scope qualifications needed to understand the comparison. |
| `left`, `right` | Recording objects described below. Left provider must be `Cerebras` for this layout. |
| `timeline` | Explicit common elapsed-time segments from `0` through the later completion. |

Each recording object requires `video`, `model`, `provider`, `start_s`, `completion_s`, `timing_evidence`, and `result_note`. `start_s` is the timestamp in the video at task submission. **`completion_s` is elapsed time since submission, not an absolute video timestamp.** Retain at least one frame of footage after completion. The renderer checks source duration and dimensions; it cannot verify that the stated boundary really is task completion. `timing_evidence` names the raw clip/log and how the boundary was established; `result_note` describes quality, limitations, and what was checked.

`crop` is optional `[x, y, width, height]` in source pixels. The default contains the complete recording with padding and no stretching. Crop only to remove irrelevant capture edges; keep task-relevant menus, results, and context. Review the result at mobile viewing size.

## Timeline and clocks

Every segment contains `from_s`, `to_s`, and `speed`. Adjacent segments must meet exactly; gaps, overlaps, reversals, and speeds below `1` are rejected. Times are elapsed task seconds shared by both panels. Segment output duration is `(to_s - from_s) / speed`.

Both recordings follow the same elapsed-time map. Each panel freezes at its own completion frame and its clock stops. A running panel displays the actual fast-forward multiplier when its segment is accelerated; a completed panel stays frozen without a fast-forward label. Place acceleration around known wait/build sections. The final second or more must be at `1x` for the result reveal. An agent must also inspect earlier result/reveal moments; the script cannot discover them.

Clocks sit at the top right of the headers, with model/provider labels on the left. Each thin progress track below the recording fills as `min(elapsed_s / completion_s, 1)` and freezes full when that side is DONE. The bars show position within the known source runs; they do not claim to estimate live inference progress or remaining work. The recording area has no extra status strip or oversized timer row.

The shipped example runs elapsed seconds `0–4` at `1x`, `4–10` at `3x`, and `10–12` at `1x`: eight seconds of comparison. Opening `2.5s` + comparison `8s` + result hold `1.5s` + DONE/logo card `2.5s` + outro `4s` = **18.5 seconds**. Timers retain the synthetic source's `4s` and `12s` completion times. The DONE card is separate from the final artwork. The branded ending shows the summary for `1.8s`, including a final `0.35s` fade, then holds the artwork without that summary. Video sampling is quantized to 24fps; displayed clocks round to tenths.

The matching [synthetic preview](synthetic-preview.mp4) and [contact sheet](synthetic-contact-sheet.png) are included so a creator can inspect the expected composition before preparing dependencies. Refresh these references after intentionally changing the composition; they are a mechanical example, not an approved performance claim or design signoff.

## Optional fields

- `background`: object containing `image` (local PNG/JPEG path relative to the manifest) and optional `fit: "cover"`. Use a 16:9 plate at least 1280×720; see [the visual library](../a reference video.md). SVG masters are supplied for editing, while the renderer consumes their PNG versions. Omit the field for a plain light background.
- `opening_s` (default 3), `result_hold_s` (default 2), `outro_s` (default 3): each at least one second. Display copy must fit; the opening rejects more than five words per second. For this social SBS layout the total must be strictly below 60 seconds. The renderer never chooses additional acceleration automatically.
- `completion_card`: object controlling the separate DONE/logo page after the result hold and before the final outro. `enabled` defaults to `true`; `duration_s` defaults to `2.5`; `partner_name` defaults to `"Partner"`; `partner_logo` is an optional local PNG path, resolved relative to the manifest. With no partner logo, the template displays an outlined “PARTNER LOGO” slot so another creator can see where the asset belongs. Supplying a logo replaces that slot's placeholder content while preserving the image's aspect ratio. Disabling the card removes its duration from the edit.
- `outro.metric`: `elapsed_time` (default) or `measured_throughput`. For measured throughput supply positive `outro.tokens_per_second` and `outro.evidence` referring to actual measurements. The renderer labels it **measured**, not “up to”; approved launch-level “up to” claims need separate evidence and an intentionally adapted card. No throughput is derived from elapsed time.
- `outro.image`: optional local full-frame ending image, resolved relative to the manifest. The supplied example uses `../assets/outros/powered-by-cerebras.png`, preserving the user's complete “powered by Cerebras” artwork. The model and supported metric appear in the free upper area before fading; the artwork remains the same card throughout.
- `outro.summary_s`: summary display time when `outro.image` is present, default `1.5` seconds. It must fit within `outro_s - 1` so the final branding hold lasts at least one second. The shipped example uses `outro_s: 4` and `outro.summary_s: 1.8`. Without an image, the renderer uses its simple metric-card fallback.

For example, this template keeps the requested placeholder visible:

```json
"completion_card": {
  "enabled": true,
  "duration_s": 2.5,
  "partner_name": "Partner"
}
```

The card uses Manrope ExtraBold for DONE, Manrope Bold for the model label, and Sometype Mono for elapsed metrics. The Cerebras logo is a rendered copy of the bundled vector wordmark; the template does not reconstruct it with a text font. Use the [font-role table](../a reference video.md) when adapting this composition.

## Outputs and limits

```sh
python3 scripts/render_demo.py --manifest path/to/demo.json --output path/to/edit --preview-only
python3 scripts/render_demo.py --manifest path/to/demo.json --output path/to/edit
```

Both commands write representative PNGs, `contact-sheet.png`, a 375px-wide `mobile-review.png`, `manifest.resolved.json`, and `timing-map.json`. The full command also writes `demo.mp4`, a **silent 1280×720, 24fps H.264** video. Recordings' source audio is muted; music, voiceover, portrait layouts, interactive result exploration, and Blender project generation are outside this initial renderer. Original asset files remain editable; the JSON and renderer reproduce the edit. Temporary normalized video data may use about 1.5GB at the maximum supported duration. Choose a new output folder for materially different edits to avoid mixing old previews with new ones.

Inspect `mobile-review.png` at its native size. Full-desktop recordings may be unreadable inside a phone-width SBS: use deliberate content crops, larger source UI, or another layout when the viewer must read details. Equal panel sizes alone do not establish readability. The renderer reserves large text for the on-screen disclosure; shorten that copy if it does not fit without shrinking it.

The evidence fields are a handoff record, not automated certification. Inspect the exported MP4's actual transition, completion, and result frames before review. A successful synthetic example establishes the rendering mechanics only; pilot real recordings before treating the skill as production-proven.

After changing the renderer, run `python3 scripts/test_renderer.py` for timing/input checks, then rerender the fixture and inspect the exported video. `python3 scripts/make_example.py` regenerates the clearly labeled fixture recordings; it is never part of preparing a real performance demonstration.
