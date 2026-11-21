---
name: cerebras-demo-basics
description: Create and review Cerebras demo videos from recordings, with reference-led framing, staged result showcases, accurate timing, and bundled branding. Also use for demo briefs or branding passes.
---
# Cerebras demo basics

Build a clear story around a real task: show the prompt, compare the experiences, demonstrate the useful result, and finish with the supported timing takeaway and logos. When the user supplies a video, inspect its whole sequence and transition boundaries before deciding on the frame or edit.

## Choose the work

- **Reference-style video:** use [reference-story.md](a reference video.md), which records the reference layout step by step, then [story-manifest-reference.md](examples/story-manifest-reference.md). This is the current requested default. View the [working example](examples/reference-story-preview.mp4) and [scene sheet](examples/reference-story-contact-sheet.png).
- **Simple legacy SBS:** `scripts/render_demo.py` and its [separate schema](examples/manifest-reference.md) retain the earlier compact layout and standalone DONE card. Do not use that separate card for the reference-story style.
- **Brief or branding only:** provide the requested brief or apply the [brand rules](a reference video.md). Do not require recordings for a brief.

Use the actual bundled fonts and logos. [visual-library.md](a reference video.md) distinguishes the usable and recreated background plates.

## Establish what is measured

Use available context to establish the audience, takeaway, confirmed models/providers, actual submitted prompts and inputs, measurement scope, selected runs, and timing evidence. Ask only for missing facts that affect the edit or claim. Keep differences in settings, tools, inputs, and output quality available to the reviewer.

**First response and task completion are different boundaries.** The reference layout stops the first-response clock while its completed side continues product exploration and a follow-up. Set each side's `stop_s` from the actual measured boundary; supply later recording ranges for that showcase. Stopping the clock does not automatically freeze the recording.

Use the same task and inputs for a comparison, documenting material setup differences. A concise displayed prompt may summarize a longer submitted prompt; retain the exact input. Different-model experience comparisons do not isolate infrastructure. Do not assume the other side runs on GPUs. Do not target a predetermined speedup or infer tokens/s from elapsed time.

## Stage the reference-style edit

1. **Prompt:** type the task in a wide composer over orange halftone. No brand-title preface.
2. **Enter the comparison:** transition into two near-full-height rounded app panels. Keep title/subtitle left and compact timer pills right; devote the frame to the recordings.
3. **Measure both:** start clocks at submission. Use explicit source ranges for each side in each scene.
4. **Show the first result:** freeze that measured clock and fade translucent DONE over that panel. Keep its real recording playing when a product/result showcase is part of the story.
5. **Use the waiting time:** demonstrate the useful output or a follow-up while the other side continues. Then hold the completed result and accelerate only the remaining wait, with its actual multiplier visible.
6. **Compare results:** dim the apps and overlay timing cards labeled with the measurement scope, such as FIRST RESPONSE.
7. **State the takeaway:** show one supported speedup on the supplied “powered by Cerebras” artwork through `speedup_background`. Use Manrope for the complete headline, including the numeric multiplier, and any supporting copy. Keep the artwork’s existing wordmark clear.
8. **Close on logos:** show Cerebras and the intended partner logo. The reusable example deliberately labels an empty slot PARTNER LOGO.

Run the current example from the skill folder:

```sh
python3 scripts/render_story_demo.py --manifest examples/reference-story.json --output story-output
```

Use `--preview-only` for the scene review sheet. Inputs, dependencies, and outputs are in the story manifest reference. The supplied footage is explicitly synthetic and demonstrates assembly only. The local renderer uses Pillow and FFmpeg, produces silent landscape video under 60 seconds, and makes no model/API calls. Blender, audio edits, and other formats need an explicitly adapted production method.

## Review and hand over

Inspect the actual export, especially measurement boundaries, continued post-response footage, per-side acceleration, DONE visibility, result labels, fonts, and logos. Review at the intended viewing size. A full desktop squeezed into a tall card may need a deliberate crop or a different capture; never stretch it. Read [production.md](a reference video.md) for the handoff and evidence checks.

Deliver the movie, editable scene manifest, timing notes, source references, and review frames. Do not publish or contact anyone unless asked. Replaying the synthetic fixture establishes the mechanics only.
