---
description: Validate CRA readiness for the secure bridge, relay, and native iOS path.
---

From the repo root:

1. Run `codex app-server --help`.
2. Run `node --check relay/server.js`.
3. Read `references/cra-charter.md`, `references/bridge/secure-bridge-protocol.md`, and `references/output-contracts.md`.
4. Summarize:
   - the warm bridge responsibilities
   - the relay's transport-only role
   - the pairing and reconnect flow
   - which paths are still fallback only
5. Do not describe Shortcuts, iMessage, or UI automation as the primary CRA architecture.
