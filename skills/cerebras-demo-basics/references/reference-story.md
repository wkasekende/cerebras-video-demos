# Reference: the comparison layout

Use this as the primary framing and sequence reference for the template. It describes an 86-second, 1920×1080 Cerebras side-by-side comparison. Its performance numbers belong to that recorded example and are not defaults for future demos.

## What the reference actually does

| Source-video time | Picture and edit | Reusable decision |
| --- | --- | --- |
| 0–8.1s | One wide white prompt composer types the shopping request over orange halftone. | Introduce the task immediately, using the prompt itself. |
| 8.1–9.4s | Composer shrinks/tilts away; two comparison cards rise into position. Prompts submit around 9.4s. | Establish both apps before starting their elapsed-time clocks. |
| 9.4–34.4s | Giant app panels fill nearly the full frame. Titles/subtitles sit left in a compact header, timer pills right. | Give almost all space to the app recordings; keep framing consistent. |
| 34.4s | Cerebras reaches 25.0 seconds. Its clock stops, and translucent DONE appears over the left app. | DONE is an in-panel state, not a separate page. |
| 36.8–62s | The left app opens products, submits a follow-up, and opens more results while DONE remains. The right continues searching. | Preserve a live post-response showcase under a frozen first-response clock. |
| 62.3–71.5s | The remaining right-side wait accelerates to 5×; the left holds its useful result. | Speed labels and clock rates belong to each side's edit independently. |
| 71.5–75s | Both apps dim. Result cards overlay 25.0 SEC and 96.1 SEC, each labeled FIRST RESPONSE. | Repeat the measured scope beside the final numbers. |
| 75–80.2s | Crossfade to an off-white halftone speedup card, reading 3.8× faster than the other side. | State one supported takeaway derived from the measurements. |
| 80.2–86.03s | A divider and Cerebras / partner logos reveal, then hold. | Finish on a clean partnership card. The reusable template uses an explicit partner-logo placeholder. |

At source resolution, the cards are approximately x 32–948 andx 972–1888, y 24–1055: a 24px gutter, compact headers, and near-full-height app content. There is no giant title or central VS occupying the comparison. The orange backdrop has pale halftone concentrated at upper-right/lower-left. DONE is a translucent terracotta rounded rectangle centered inside the completed panel.

The source measures **first response**, not completion of every later click or follow-up. The left clock remains 25.0 while the app continues. Do not assign those showcase actions additional first-response time, and do not freeze the app automatically when its measurement stops.

The exact source font families cannot be identified from video pixels alone. Reuse the user's original bundled font files: Manrope for headers/labels, Sometype Mono for elapsed times, and Instrument Sans for the composer. Do not claim a raster comparison proves a font identity.

## Build a new edit in this mode

The user's later template adjustment places the speedup headline on the supplied “powered by Cerebras” artwork, using Manrope text. The source-video table above remains a factual description of the original light ending; the current template uses `speedup_background` for the requested branded variation.

1. Agree on the audience, task, model/provider labels, and what the time measures. Keep the actual prompts, selected runs, results, and timing evidence.
2. Use near-square/portrait app captures that fill the tall cards. Crop deliberately to the useful app window; never stretch a widescreen desktop capture to fill it.
3. Set each side's `stop_s` to its verified measurement boundary. Supply later footage for any post-response showcase.
4. Write a scene list with explicit source ranges or holds for each side. A range may continue past `stop_s` while that clock stays frozen. Keep pre-response activity chronological and disclose per-side acceleration.
5. Stage the prompt, panel entrance, live comparison, in-panel DONE, result showcase, remaining wait, result cards, speedup, and partnership card in that order.
6. Inspect the exported video around both measurement boundaries and every speed change. Verify DONE does not hide the useful result and that post-response footage actually continues when requested.
7. Use the shorter scene timings in the bundled synthetic example for an under-one-minute template. The source video's 86-second runtime is a reference, not the target length.

```sh
python 3 scripts/render_story_demo.py --manifest examples/reference-story.json --output story-output
```

The supplied shopping footage is illustrative code-drawn UI and products. Its 4s/20s first-response times demonstrate scene mechanics only; they are not model results. The final partner slot is intentionally a placeholder, as requested by the user. The earlier `render_demo.py` remains a simpler legacy mode with its own schema and separate DONE card; do not use that layout to approximate this reference.
