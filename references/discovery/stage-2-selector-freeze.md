# Stage 2 Fallback Selector Freeze Notes

These notes describe the fallback selector-freeze path for the hybrid-native prototype. They are not the primary CRA architecture after the App-Server-first pivot.

## Current Snapshot

The current snapshot was captured with:

```bash
python3 -m cra.cli probe-ui --output references/discovery/codex-ui-probe.json
```

Current result:

- Process visible: `Codex`
- Window visible: `Codex`
- Buttons discovered: `0`
- Structured snapshot: `references/discovery/codex-ui-probe.json`
- Low-level AX tree snapshot: `references/discovery/codex-ax-tree.json`
- `AXManualAccessibility` successfully enabled on the running Codex PID

## Interpretation

- `System Events` can see the Codex process and current front window.
- `System Events` still does not expose button-role nodes that are sufficient for freezing approve/deny selectors.
- The low-level AX tree now exposes a richer Electron accessibility surface, including DOM-oriented attributes such as `AXDOMIdentifier` and `ChromeAXNodeId`.
- The current idle window still surfaces mostly `AXGroup` nodes plus standard window controls, so approve or deny selectors are still not available in the current snapshot.
- This means the selector freeze is blocked on one of two conditions:
  - a real approval prompt must be visible when the probe runs, or
  - a different Accessibility exposure path must be identified

## Next Capture Procedure

1. Trigger a real Codex approval prompt and leave it visible.
2. Run:

```bash
python3 -m cra.cli enable-manual-accessibility --bundle-id com.openai.codex --app-name Codex --pid <PID> --prompt-trust
python3 -m cra.cli dump-ax-tree --pid <PID> --max-depth 6 --max-children 40 --output references/discovery/codex-ax-tree.json
python3 -m cra.cli probe-ui --output references/discovery/codex-ui-probe.json
```

3. Inspect both snapshots for the approve and deny controls.
4. Copy the final `AXDescription` values into `config/codex-selectors.json`, based on `config/codex-selectors.example.json`.
5. Validate with:

```bash
python3 -m cra.cli actuate-local --decision approve --action-id 11111111-1111-4111-8111-111111111111 --allow-live --selector-config config/codex-selectors.json
```

## Safety Rule

Do not enable live actuation until both approve and deny selectors are frozen and confirmed against a visible approval prompt.
