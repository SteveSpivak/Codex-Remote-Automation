---
description: Validate CRA readiness for the upstream Remodex path, relay decision work, and native iOS proof.
---

From the repo root:

1. Run `codex app-server --help`.
2. Read `references/cra-charter.md`, `references/research/remodex-upstream-assessment.md`, and `references/output-contracts.md`.
3. If the task touches the in-repo relay, run `node --check relay/server.js`.
4. Summarize:
   - the upstream proof status
   - the chosen relay assumptions
   - the pairing and reconnect flow
   - the current wrapper-vs-fork decision
   - which paths are still fallback only
5. Do not describe Shortcuts, iMessage, or UI automation as the primary CRA architecture.
