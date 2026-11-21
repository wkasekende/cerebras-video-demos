# Reference-story manifest

Use this schema with `scripts/render_story_demo.py`. It reproduces the framing and scene order documented in [reference-story.md](../a reference video.md). The shorter synthetic example does not copy the original video's 86-second duration or performance claims.

## Start here

```sh
python3 scripts/render_story_demo.py --manifest examples/reference-story.json --output story-output --preview-only
python3 scripts/render_story_demo.py --manifest examples/reference-story.json --output story-output
```

Use Python 3.10+, Pillow, and FFmpeg; the existing [runtime setup](manifest-reference.md#runtime) applies. Local paths resolve relative to the manifest's directory. No model access, live task execution, or upload occurs.

The output is a silent 1280×720, 24fps H.264 MP4 with scene review images, a contact sheet, a resolved manifest, and a timing map. Preserve the originals and use a fresh output directory for materially different edits.

## Overall edit fields

| Field | Meaning |
| --- | --- |
| `schema_version`, `layout` | `1` and `"reference_story"`. |
| `synthetic` | Explicit boolean. Keep true for the included illustrative shopping footage. |
| `title` | Short task subtitle in both headers. |
| `display_prompt`, `full_prompt` | Readable opening and actual shared submitted task. Retain differences and setup notes when adapting real runs. |
| `disclosure` | Short readable scope/test label. The fixture uses “Synthetic template · Not a benchmark.” |
| `measurement_label` | Scope printed on the result cards, e.g. `FIRST RESPONSE`. Set this from what the timing evidence actually measures. |
| `background`, `closing_background` | Local 16:9 plates for the orange comparison and light partnership close. |
| `speedup_background` | Optional local 16:9 plate for the speedup page; falls back to `closing_background` when omitted. The supplied example uses `../assets/outros/powered-by-cerebras.png` so the speed claim and powered-by branding share the same page. |
| `opening_s`, `transition_s`, `start_hold_s` | Prompt typing, panel entrance, and established panels before the recordings advance. |
| `result_cards_s`, `speedup_card_s`, `logos_s` | Holds for the result overlays, speedup, and partnership close. |
| `partner_name`, `partner_logo` | Partner identity and optional local raster asset. The template uses `PARTNER LOGO` and no asset, making the replacement slot explicit. Do not infer a partner from the model name. |

The shipped example has 4.5s prompt + 0.75s transition + 0.25s start hold + 15s comparison scenes (including a 1s final response hold) + 2.5s result overlays + 2.5s speedup + 3s logos = **28.5 seconds**. A different source or scene list needs its own timings; the renderer rejects social edits of 60 seconds or longer.

## Recording objects

Both `left` and `right` contain:

- `video`: actual source recording, with enough footage for every listed scene.
- `title`: display name in the compact header; identify model/provider accurately.
- `label`: concise result-card label.
- `start_s`: source-video timestamp corresponding to task submission.
- `stop_s`: **elapsed seconds after submission at the verified measurement boundary**. This is neither the absolute source timestamp nor the end of all showcase footage.
- `timing_evidence`, `result_note`: source/log reference, boundary rationale, and output-quality context.

Clocks show `min(source_elapsed_s, stop_s)`. When a measurement stops, DONE appears and the associated thin run-position bar is full. The clip may continue through later source ranges while those indicators stay frozen. That bar is an editing aid based on an already recorded boundary, not an estimate of live work completed.

The fixture's left response is at 4s and right response at 20s. Its left source continues through product details and a follow-up to 11s elapsed. All content and timings are illustrative; the example supports no model-performance claim.

## Scene list: independent playback for each side

Each scene has `label`, positive `duration_s`, and one mapping for each side:

```json
{
  "label": "Explore the first result while the other side waits",
  "duration_s": 4,
  "left": {"from_s": 4, "to_s": 8},
  "right": {"from_s": 4, "to_s": 8}
}
```

Source values are elapsed seconds since that side's submission. Playback speed is `(to_s-from_s)/duration_s`. Before the measurement boundary, keep footage chronological with no omitted source time; make acceleration visible.

For a held completed result, use `{"hold_s": 11}`. Holding is distinct from a source range. In the included remaining-wait scene, the left holds at 11s while the right plays 11–19s over 2 output seconds: a 4× right-side speed label appears, and the frozen left clock remains 4s.

The source video's 5× badge belongs to its own edit. Do not hardcode it into a scene with different source/output durations. Inspect the result reveal at normal speed and keep the final useful output readable before the result overlays.

## Mode boundaries

This mode ends with timing overlays → speedup on the supplied powered-by artwork → Cerebras/partner logos. It does not insert the earlier standalone DONE page. The complete speedup headline, including the numeric multiplier, uses bundled Manrope Medium (`manrope-500.ttf`) with tight `-0.065em` tracking; supporting copy uses the same face. Both use warm off-white `#EBE4DB` to visually match the supplied powered-by lettering. Place added text in the artwork’s free upper area and preserve its existing wordmark. The partner-logo page still uses the quiet light `closing_background`.

The legacy [basic manifest](manifest-reference.md) belongs to `render_demo.py` and cannot be passed to this scene renderer. Exact source fonts cannot be inferred from video pixels: use the bundled brand-font roles for new text, preserving the original captured app UI.
