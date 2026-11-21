# Bundled brand rules

Use these defaults for the framing and overlays. Preserve the content and colors of the actual recorded product.

- **Cerebras:** orange `#F15A29`.
- **Other side:** neutral gray `#555650`; use an accurate model/provider label rather than assuming its hardware.
- **Panels:** white or `#FDFDFD`; supporting surfaces `#F4F4F1`; primary text `#252525`.
- Favor light mode and sparse text. Avoid green in the added demo branding.
- Use the bundled local font files by the roles below. Do not silently substitute a system font or claim a fallback is one of these families. Recorded product UI keeps its original typography.
- `assets/cerebras-logo.png` and `assets/cerebras-wordmark.svg` are the supplied logo files. The DONE card uses `assets/cerebras-wordmark-rendered.png`, rendered from that SVG, rather than typing a substitute wordmark. Keep logo proportions intact. Use supplied Cerebras branding by default; preserve user-approved partner branding where appropriate.

| Added text | Bundled font |
| --- | --- |
| In-panel DONE label | Manrope ExtraBold, `manrope-800.ttf` |
| Model names and headings | Manrope Bold, `manrope-700.ttf` |
| Powered-by speedup page: complete headline and supporting text | Manrope Medium, `manrope-500.ttf`, warm `#EBE4DB`; headline tracking `-0.065em` |
| Supporting labels and disclosure | Manrope SemiBold/Bold, `manrope-600.ttf` / `manrope-700.ttf` |
| Clocks and numeric metrics | Sometype Mono SemiBold/Bold, `sometype-mono-600.ttf` / `sometype-mono-700.ttf` |
| Prompt composer | Instrument Sans, `instrument-sans-latin.woff2` |

## Reference-story composition (current default)

Use one quiet background and equal panel dimensions. Put model/provider labels on the left of each header and a compact clock at the top right. Give the recording the main panel area, without a separate oversized timer row or status strip. Frame both recordings at a comparable scale. Preserve task-relevant menus, inputs, output, and completion evidence; do not crop them away to fill the panel. Rounded panel corners should conceal capture-edge artifacts without hiding content.

Place a thin progress track beneath each recording, following the supplied reference's pale track and colored fill. Cerebras uses orange; the comparison uses neutral gray. Fill represents elapsed time divided by the known recorded-run duration, reaches full at that side's verified completion, and stays there. Do not present it as a live estimate of work completed or remaining.

Match the reference frame: near-full-height white rounded cards over orange halftone, with compact titles/subtitles left and timer pills right. The source uses seconds with one decimal and SEC, rather than the legacy minutes/seconds format. Keep DONE as a translucent terracotta badge over the measured side, with white Manrope lettering. Its clock freezes at the measured boundary; the app footage can keep demonstrating results beneath it. Hold the app only when that scene explicitly calls for a held result. During accelerated playback, show the actual multiplier over that side. Original elapsed time, playback speed, and measured tokens/s remain separate quantities.

## Reference-story ending

Dim the app panels and overlay separate timing cards, each labeled with the actual measurement scope (FIRST RESPONSE in the supplied reference). The current template then places the supported speedup on the supplied `assets/outros/powered-by-cerebras.png` through `speedup_background`, followed by a Cerebras / partner logo row on the quiet light closing plate. Match the supplied powered-by lettering with Manrope Medium (`manrope-500.ttf`), tight headline tracking (`-0.065em`), and warm off-white `#EBE4DB` for the entire speedup headline and supporting text. This is a visual match to the flattened artwork, whose PNG metadata does not identify its typeface. This text sits in the artwork’s free upper area; retain the powered-by wordmark already in the asset without adding a duplicate. Numeric clocks/result fields remain Sometype Mono. Keep the placeholder visibly labeled in reusable template output. The model partner can differ from the comparison provider: the close shows Cerebras and the model or launch partner, not necessarily the provider being compared against.

## Legacy DONE card and alternate ending

After the comparison and result hold, use a separate DONE card with a large Manrope ExtraBold heading, the relevant model, verified elapsed metrics in Sometype Mono, and a logo row. The Cerebras wordmark and partner slot sit on a light logo panel. Keep both logos contained within their slots with their original aspect ratios. The reusable template explicitly labels an empty partner slot “PARTNER LOGO”; it is a placement guide, not a fabricated partner identity. Replace it with the supplied asset through `completion_card.partner_logo` for a partner-specific edit. Do not infer a partner from a model label alone.

The supplied `assets/outros/powered-by-cerebras.png` is the user's full-frame ending artwork, including its wordmark. Preserve its proportions and use it directly rather than rebuilding the logo. Show the relevant model and supported metric in the free upper area briefly, then fade the summary so the final hold emphasizes the supplied “powered by Cerebras” card. Keep the disclosure readable and leave at least one second for the final branding hold. Prefer the metric the demo actually demonstrated; do not insert a throughput number merely to fill the card. Without `outro.image`, the renderer retains its simple metric-card fallback.

The original package contained fonts and logos. The bundled backgrounds are geometric recreations; see [visual-library.md](visual-library.md). This bundled SBS composition does not establish approval of a new design.
