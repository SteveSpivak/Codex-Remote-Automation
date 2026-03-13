---
description: Inspect the current CRA upstream path, wrapper status, and fallback status without mutating the repo.
---

From the repo root:

1. Run `codex app-server --help` and `codex exec --help`.
2. Read `references/research/remodex-upstream-assessment.md`.
3. Run `python3 -m cra.cli discover`.
4. Summarize the upstream-first architecture, the current wrapper or compatibility-study status, and the main blockers to a live paired mobile client.
5. Treat Shortcuts, iMessage, Accessibility, and OCR findings as fallback-only unless the user explicitly asks to work on them.
