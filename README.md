# Codex Remote Automation

Codex Remote Automation (CRA) is an App-Server-first architecture for adding a human-in-the-loop approval broker to Codex on macOS. The primary design is protocol-based: Codex emits approval requests through `codex app-server`, a local CRA broker normalizes and audits them, an iPhone approval surface returns the operator's decision, and the broker resolves the request back to Codex.

This repository contains the project charter, specialist CRA skills, repo-native Codex guidance, and a fallback hybrid-native prototype. The current `cra/` Python package, Accessibility helpers, and OCR discovery flow remain in the repo for fallback and discovery work only; they are not the primary architecture.

## Architecture Summary

- Primary path: `codex app-server` -> local CRA broker -> iPhone approval surface -> broker decision response -> Codex
- Replay and testing path: `codex exec --json` and App Server protocol fixtures
- Fallback path: the existing Shortcuts plus Accessibility/OCR prototype under `cra/`, `scripts/`, and `references/discovery/`
- Security model: private transport only, protocol-aware audit logging, no public exposure, and human approval preserved throughout

## Repository Layout

```text
.
|-- .codex/
|   |-- config.toml
|   `-- commands/
|-- AGENTS.md
|-- README.md
|-- cra/
|-- launchd/
|-- references/
|   |-- cra-anti-patterns.md
|   |-- cra-charter.md
|   |-- cra-standards.md
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

## Protocol Quick Start

Use these commands to validate the App Server and replay surfaces from the repo root:

```bash
codex app-server --help
codex exec --help
python3 -m cra.cli broker-replay --input tests/fixtures/broker_command_flow.jsonl --auto-decision decline
python3 -m cra.cli broker-summarize
python3 -m unittest discover -s tests -p 'test_*.py'
```

Repo-native Codex commands are checked in under `.codex/commands/`:

- `/cra-tests`
- `/cra-discovery`
- `/cra-app-server-readiness`

## Fallback Prototype Quick Start

Run the existing hybrid-native checks only for fallback discovery or emergency UI experimentation:

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

The fallback prototype uses `action_id`, Accessibility selectors, and OCR helpers. Those contracts are intentionally scoped to discovery docs and prototype testing.

## Core Docs

- [Project charter](references/cra-charter.md)
- [CRA standards](references/cra-standards.md)
- [CRA anti-patterns](references/cra-anti-patterns.md)
- [CRA output contracts](references/output-contracts.md)
- [Shortcuts runbook](references/shortcuts-runbook.md)
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
