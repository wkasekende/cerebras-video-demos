# Backgrounds

This package includes usable background plates, not only color instructions. Set `background.image` in the edit manifest; paths are relative to that manifest. The renderer preserves readable light panels and a light disclosure strip over any selected background.

| Asset in `assets/backgrounds/` | Size | Use |
| --- | --- | --- |
| `reference-orange-halftone.png` / `.svg` | 3840×2160 | The orange halftone behind the comparison and the prompt. A geometric recreation of the reference layout's look; the default for the examples. |
| `reference-light-halftone.png` / `.svg` | 3840×2160 | The low-contrast light halftone for the partnership close. |
| `light-halftone-recreated.png` / `.svg` | 3840×2160 | Quiet neutral field with orange halftone corners; useful when a comparison needs less background activity. |
| `light-grid-recreated.png` / `.svg` | 3840×2160 | Quiet neutral field with a fine orange grid. |

The SVG masters are editable vector assets. The PNG versions use the same geometry and are ready for the video renderer. `python3 scripts/build_backgrounds.py` regenerates the two recreated plates; `python3 scripts/make_story_example.py` regenerates the two reference plates. They are newly generated artwork, not original design-tool exports, and they have not been approved as original brand templates.

For a manifest stored in `examples/`, select a background with:

```json
"background": {
  "image": "../assets/backgrounds/light-halftone-recreated.png",
  "fit": "cover"
}
```

Use a full 16:9 PNG/JPEG at least 1280×720. Do not pass a screenshot or a montage as the plate: those contain existing UI or several thumbnails. The current output is 1280×720 even when the source plate is 4K.

## The powered-by ending

`assets/outros/powered-by-cerebras.png` is the full-frame 3840×2160 "powered by Cerebras" artwork, preserved as supplied. The story template selects it with `speedup_background` for the speedup page. Use Manrope for the headline and supporting text in the free upper area. The artwork already contains the wordmark, so do not place a duplicate logo over it.

The renderer draws a slim progress track beneath each recording (a pale track with a colored fill, orange for Cerebras and neutral gray for the other side) and compact clocks at the top right of the panel headers.

In the legacy basic renderer, a separate DONE card with the Cerebras wordmark and a partner-logo slot comes before the final artwork. `assets/cerebras-wordmark-rendered.png` is rendered from the bundled `assets/cerebras-wordmark.svg` for that card. The default template labels an empty slot "PARTNER LOGO"; `completion_card.partner_logo` accepts the intended partner's logo.
