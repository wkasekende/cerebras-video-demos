# Contributing

This kit is a baseline for your creativity: a new scene, a theme in your brand colours, a language, a layout. Fork it and ask your agent of choice to extend it; `templates/EXTENDING.md` has the rules and a prompt to paste.

To send a change back:

1. Run `python3 tools/make-film.py --check` (seconds) and, for engine, theme or scene changes, the full gate: `bash tools/agent-film-check.sh` (about 25 minutes; it ends with `OK`).
2. Reuse the existing colour tokens and weights; make every component progressive and every length derived (`EXTENDING.md`, "The rules").
3. Add a staged refusal and a verifier check for anything new, and a still of it in every theme.
4. Open a pull request saying what it adds and showing the stills.

By contributing you agree your contribution is licensed under the Apache License 2.0.
