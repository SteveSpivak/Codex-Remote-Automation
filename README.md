# Codex Remote Automation

Codex Remote Automation (CRA) is an approval-first remote control plane for Codex on macOS. The phone-compatible primary path is now Remodex-style: the Mac keeps a warm `codex app-server` session alive, a Remodex-compatible bridge encrypts mobile traffic, a self-hosted WebSocket relay forwards only opaque envelopes, and the Remodex iPhone app connects over the bridge protocol.

This repository contains the Remodex-compatible bridge code, the self-hosted relay, a CRA iOS client skeleton for future custom work, specialist CRA skills, repo-native Codex guidance, and explicit fallback tooling. Shortcuts, iMessage, Accessibility, AppleScript, and OCR remain in the repo as transitional or discovery paths only.

## Architecture Summary

- Primary path: `codex app-server` -> warm Remodex-compatible bridge -> encrypted session envelopes -> self-hosted relay -> Remodex iPhone app -> bridge decision response -> Codex
- Replay and testing path: `codex exec --json`, broker replay fixtures, and bridge protocol tests
- Transitional fallback path: Shortcuts or iMessage for operator decisions when the Remodex app path is unavailable
- Discovery/emergency fallback path: Accessibility, AppleScript, screenshot, and OCR helpers under `cra/`, `scripts/`, and `references/discovery/`
- Security model: relay is transport-only, approval payloads remain encrypted in transit, replay protection is mandatory, and human approval is preserved throughout

## Repository Layout

```text
.
|-- .codex/
|   |-- config.toml
|   `-- commands/
|-- AGENTS.md
|-- README.md
|-- cra/
|   `-- bridge/
|-- ios/
|   `-- CRAOperatorApp/
|-- relay/
|-- launchd/
|-- references/
|   |-- cra-anti-patterns.md
|   |-- cra-charter.md
|   |-- cra-standards.md
|   |-- bridge/
|   |-- discovery/
|   |-- output-contracts.md
|   `-- shortcuts-runbook.md
|-- security/
|-- scripts/
`-- skills/
    |-- cra-backend-developer/SKILL.md
    |-- cra-macos-engineer/SKILL.md
    |-- cra-network-architect/SKILL.md
    |-- cra-orchestrator/SKILL.md
    |-- cra-security-specialist/SKILL.md
    `-- cra-test-engineer/SKILL.md
```

## Remodex Bridge Quick Start

Use these commands from the repo root to exercise the primary bridge path:

```bash
node relay/server.js
node remodex/bridge.js --relay-url ws://127.0.0.1:8787 --pair-only
node remodex/bridge.js --relay-url ws://127.0.0.1:8787
codex app-server --help
codex exec --help
python3 -m cra.cli broker-replay --input tests/fixtures/broker_command_flow.jsonl --auto-decision decline
python3 -m cra.cli broker-summarize
python3 -m unittest discover -s tests -p 'test_*.py'
node --test tests/node/*.test.js
node --check relay/server.js
```

Repo-native Codex commands are checked in under `.codex/commands/`:

- `/cra-tests`
- `/cra-discovery`
- `/cra-app-server-readiness`
- `/cra-bridge-readiness`

The Remodex-compatible bridge source lives under [remodex](/Users/steve.spivak/Documents/MAcosAutomation/remodex). The in-repo CRA iOS operator client source still lives under [CRAOperatorApp](/Users/steve.spivak/Documents/MAcosAutomation/ios/CRAOperatorApp), but it is now secondary/experimental rather than the primary mobile path.

## Transitional Fallback Quick Start

Run the Shortcuts or iMessage path only while the native iOS app is incomplete or unavailable:

```bash
python3 -m cra.cli broker-service --prompt "Run git status and wait for approval"
python3 -m cra.cli broker-pending
python3 -m cra.cli broker-shortcut-payload
python3 -m cra.cli broker-respond --request-id <request_id> --decision decline
python3 -m cra.cli build-broker-response-ssh-command --request-id <request_id> --decision decline --operator-note "Optional audit note"
python3 -m cra.cli imessage-poll --handle <your-imessage-handle>
python3 -m cra.cli imessage-parse --text "decline <request_id>"
```

## Discovery And Emergency Fallback

Run the hybrid-native checks only for fallback discovery or emergency UI experimentation:

```bash
python3 -m cra.cli discover
python3 -m cra.cli summarize-sentry
python3 -m cra.cli enable-manual-accessibility --bundle-id com.openai.codex --app-name Codex --pid <PID> --prompt-trust
python3 -m cra.cli dump-ax-tree --pid <PID> --max-depth 6 --max-children 40 --output references/discovery/codex-ax-tree.json
python3 -m cra.cli probe-ui --output references/discovery/codex-ui-probe.json
cp config/codex-selectors.example.json config/codex-selectors.json
python3 -m cra.cli capture-window-ocr --app-name Codex --output references/discovery/codex-window-ocr.json --image-output var/captures/codex-window.png --target-text Approve --required-context "Tool approval"
python3 -m cra.cli shortcut-entry --decision approve --action-id 11111111-1111-4111-8111-111111111111
```

The discovery path uses `action_id`, Accessibility selectors, and OCR helpers. Those contracts are intentionally scoped to fallback docs and prototype testing.

## Core Docs

- [Project charter](references/cra-charter.md)
- [CRA standards](references/cra-standards.md)
- [CRA anti-patterns](references/cra-anti-patterns.md)
- [CRA output contracts](references/output-contracts.md)
- [Secure bridge protocol](references/bridge/secure-bridge-protocol.md)
- [Remodex bridge notes](remodex/README.md)
- [Shortcuts runbook (fallback)](references/shortcuts-runbook.md)
- [Shortcut build pack](references/shortcuts/cra-operator-shortcut.md)
- [Stage 0 fallback feasibility notes](references/discovery/stage-0-feasibility.md)
- [Stage 2 fallback selector notes](references/discovery/stage-2-selector-freeze.md)
- [Stage 3 fallback hybrid-native notes](references/discovery/stage-3-hybrid-native.md)

## Skills

- [CRA orchestrator](skills/cra-orchestrator/SKILL.md)
- [CRA backend developer](skills/cra-backend-developer/SKILL.md)
- [CRA macOS engineer](skills/cra-macos-engineer/SKILL.md)
- [CRA network architect](skills/cra-network-architect/SKILL.md)
- [CRA security specialist](skills/cra-security-specialist/SKILL.md)
- [CRA test engineer](skills/cra-test-engineer/SKILL.md)
