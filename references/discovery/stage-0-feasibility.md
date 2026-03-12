# Stage 0 Fallback Feasibility Notes

These notes capture the pre-pivot discovery workflow against the local Codex installation. They are retained for fallback and historical discovery only after the App-Server-first realignment.

## Confirmed Local Surfaces

- Codex app bundle: `/Applications/Codex.app`
- Codex profile directory: `~/Library/Application Support/Codex`
- Codex log directory: `~/Library/Logs/com.openai.codex`
- Structured telemetry file: `~/Library/Application Support/Codex/sentry/scope_v3.json`
- Local storage log: `~/Library/Application Support/Codex/Local Storage/leveldb/LOG`

## What The Current Machine Tells Us

- The log directory exists but currently does not expose readable plain-text files.
- The Sentry scope file contains:
  - Electron and HTTP breadcrumbs
  - UI click breadcrumbs with selector-like messages and `aria-label` strings
  - app/runtime metadata for Codex, Electron, Node, and macOS
- The LevelDB log exists, but it currently looks like storage housekeeping rather than a clean event feed.
- A live `System Events` probe can see the Codex process and window, but the idle Codex window did not expose actionable button-role elements in the current snapshot.

## Historical Default Decision

Use two discovery paths in parallel:

1. `python3 -m cra.cli summarize-sentry`
   - Establish whether the Sentry scope file changes fast enough and with enough semantic value to detect approval-related state.
2. `osascript scripts/cra_probe_codex_ui.applescript`
   - Capture real Accessibility labels and button descriptions from the running Codex window.
3. `python3 -m cra.cli probe-ui --output references/discovery/codex-ui-probe.json`
   - Save a structured selector snapshot into the repo for later freeze and comparison.

Do not assume a conventional app log file is the correct watcher surface until one is actually observed.

## Commands

```bash
python3 -m cra.cli discover
python3 -m cra.cli summarize-sentry
python3 -m cra.cli emit-synthetic-event --context "Stage 0 probe" --risk-level low
osascript scripts/cra_probe_codex_ui.applescript
```

## Freeze Criteria

Stage 0 is complete when all of the following are true:

- One outbound event surface is selected and justified.
- One inbound UI selector strategy is selected and justified.
- The fallback `ApprovalEvent` contract is stable.
- The fallback inbound `decision + action_id` contract is stable.
- The synthetic event path can drive local validation without live Codex prompts.
- A Codex approval prompt has been captured while visible, and its approve/deny controls have been frozen into `config/codex-selectors.json`.
