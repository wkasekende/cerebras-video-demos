# The faces, identified

Two families, both read out of the files' own name tables with
`node font-name.mjs <file>` (no guessing from the letterforms), both
open-licence (SIL OFL 1.1, on Google Fonts), both what cerebras.ai ships.

| role | family | what cerebras.ai preloads | file here |
|---|---|---|---|
| **sans** (headings, body, UI) | **Manrope**, variable, weight 200 to 800 | `/_next/static/media/a343f882a40d2cc9.p.71e1367e.woff2`: Manrope with an `fvar` axis, default instance ExtraLight 200, Latin | `cerebras/Manrope[wght].woff2` (the full variable file); `cerebras/Manrope.site.woff2` is the site's own byte-identical preload, kept as the proof |
| **mono** (dates, labels, buttons, the disclaimer strip) | **Sometype Mono**, variable, weight 400 to 700 | `/_next/static/media/4fa648fc9ea23799.p.5a7eb4f9.woff2`: Sometype Mono SemiBold 600, fixed pitch | `cerebras/SometypeMono[wght].woff2`; `cerebras/SometypeMono-SemiBold.site.woff2` the site's preload |

How each is used on cerebras.ai, read off the screenshots: Manrope at
light weights for display (BLOG in the hero band, "Schedule a meeting"),
regular for body, medium for card titles; Sometype Mono at SemiBold,
uppercase, letter-spaced, small, for dates (`AUGUST 18, 2026`), footer
labels (`FOLLOW`, `COMPANY`), buttons (`CONTACT US`), author tags and the
disclaimer strip.

In this folder: `sheet.css` sets `--font-sans: 'Manrope'` and `--font-mono:
'Sometype Mono'`; `build.py` inlines the two variable files into every
built page (film, inline, review pages), so a render on any machine draws
the same faces. `DEMOKIT_FONTS` points at another folder with the same file
names.

## Other scripts: the fallback face

Manrope and Sometype Mono are Latin faces. A config in Arabic, Chinese,
Japanese or Korean needs glyphs they do not have, and a page cannot leave
that to whichever font the viewing machine happens to own (a render in the
cloud owns almost none). So `build.py` adds one more family to every stack,
**`DemoKit Fallback`**, and fills it per script with a face SUBSET to the
characters the page actually uses (`pyftsubset`, from fonttools; `pip
install fonttools brotli`), inlined like the others. Latin keeps coming from
Manrope because it comes first in the stack; the fallback only answers for
the ranges the site's faces lack (`@font-face` with a `unicode-range`).

| script | ranges | the face used, first that exists |
|---|---|---|
| `arabic` | Arabic, Arabic Supplement and Extended-A, Presentation Forms A and B | `fonts/fallback/arabic.ttf` (or `.otf`), else Noto Sans Arabic, DejaVu Sans, Arial Unicode, Segoe UI where the machine has them |
| `cjk` | CJK Unified and Extension A, kana, Hangul, Compatibility, full-width forms | `fonts/fallback/cjk.ttf` (or `.otf`, `.ttc`), else Noto Sans CJK, Droid Sans Fallback, PingFang, Microsoft YaHei where the machine has them |

**Choose the face by dropping it in `fonts/fallback/`.** Nothing heavy is
committed: the machine's own files are the default, so a fresh clone on a
machine with none of them builds the page with a warning and the viewer's
fonts fill the family. A brand-quality cut wants a chosen face in that
folder, and the table in `build.py` (`SCRIPTS`) is where a new script or a
new candidate path goes. The subset is cached under `out/_fonts/` by face
and character set, so a rebuild with the same text costs nothing.

The review page's shell (`artifact/pagestyle.py`) takes the page's text the same way,
so the five-language page carries every script it shows.
