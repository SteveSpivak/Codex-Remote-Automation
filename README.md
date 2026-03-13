# Codex Remote Automation

Codex Remote Automation (CRA) is an approval-first remote control plane for Codex on macOS. The current implementation strategy is upstream-first: prove the official [Remodex](https://github.com/Emanuele-web04/remodex) package and iPhone app work end-to-end, wrap them thinly for CRA audit and policy needs, and fork only where the upstream package cannot satisfy a hard requirement.

This repository contains CRA skills, repo-native Codex guidance, the existing CRA broker and fallback tooling, and a `remodex/` compatibility-study folder that is no longer the canonical implementation path.

## Architecture Summary

- Primary proof path: official `remodex up` -> official Remodex iPhone app -> selected relay path -> Codex
- CRA extension path: thin wrapper around upstream bridge outputs for approval audit, policy, and local operator guidance
- Replay and testing path: `codex exec --json`, broker replay fixtures, and upstream bridge validation checks
- Transitional fallback path: Shortcuts or iMessage for operator decisions when the Remodex app path is unavailable
- Discovery and emergency fallback path: Accessibility, AppleScript, screenshot, and OCR helpers under `cra/`, `scripts/`, and `references/discovery/`
- Fork gate: do not reimplement the bridge or relay until upstream `remodex` completes a known-good phone pairing for the target environment

## Repository Layout

```text
.
|-- .codex/
|   |-- config.toml
|   `-- commands/
|-- AGENTS.md
|-- README.md
|-- cra/
|-- ios/
|   `-- CRAOperatorApp/
|-- relay/
|-- remodex/
|-- launchd/
|-- references/
|   |-- bridge/
|   |-- discovery/
|   |-- research/
|   |-- cra-anti-patterns.md
|   |-- cra-charter.md
|   |-- cra-standards.md
|   |-- output-contracts.md
|   `-- shortcuts-runbook.md
|-- scripts/
`-- skills/
```

## Upstream Remodex Quick Start

Use these commands to validate the official upstream path first:

```bash
npm install -g remodex@latest
remodex up
remodex resume
remodex watch
```

If you need to override the relay during local testing, use `REMODEX_RELAY=... remodex up`.

Use these repo-local commands to inspect the CRA environment around that upstream path:

```bash
codex app-server --help
codex exec --help
python3 -m cra.cli broker-replay --input tests/fixtures/broker_command_flow.jsonl --auto-decision decline
python3 -m cra.cli broker-summarize
python3 -m unittest discover -s tests -p 'test_*.py'
node --test tests/node/*.test.js
```

Repo-native Codex commands are checked in under `.codex/commands/`:

- `/cra-tests`
- `/cra-discovery`
- `/cra-app-server-readiness`
- `/cra-bridge-readiness`

## Upstream Research Notes

Current findings from the upstream README, installed npm package, and local runtime checks:

- The official npm package exposes `remodex up`, `remodex resume`, and `remodex watch`.
- Upstream defaults `REMODEX_RELAY` to `wss://api.phodex.app/relay`.
- The upstream README says the full phone-to-Mac flow still depends on `api.phodex.app` during the current testing phase.
- The README says self-hosting is supported in principle and the relay code is available, but that does not make every local `ws://` setup a known-good production path.
- The bridge persists state under `~/.remodex` and, on macOS, attempts Keychain-backed storage for bridge identity.
- `REMODEX_PUSH_SERVICE_URL` can be overridden or emptied, but hosted relay and notification expectations still need proof in the target environment.

See [upstream research notes](references/research/remodex-upstream-assessment.md) for the current evidence set.

## Transitional Fallback Paths

Run the Shortcuts or iMessage path only while the upstream Remodex path is unavailable or under investigation:

```bash
python3 -m cra.cli broker-service --prompt "Run git status and wait for approval"
python3 -m cra.cli broker-pending
python3 -m cra.cli broker-shortcut-payload
python3 -m cra.cli broker-respond --request-id <request_id> --decision decline
python3 -m cra.cli build-broker-response-ssh-command --request-id <request_id> --decision decline --operator-note "Optional audit note"
python3 -m cra.cli imessage-poll --handle <your-imessage-handle>
python3 -m cra.cli imessage-parse --text "decline <request_id>"
```

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

## Core Docs

- [Project charter](references/cra-charter.md)
- [CRA standards](references/cra-standards.md)
- [CRA anti-patterns](references/cra-anti-patterns.md)
- [CRA output contracts](references/output-contracts.md)
- [Secure bridge protocol notes](references/bridge/secure-bridge-protocol.md)
- [Upstream Remodex research](references/research/remodex-upstream-assessment.md)
- [Remodex compatibility-study notes](remodex/README.md)
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
- [CRA upstream integration](skills/cra-upstream-integration/SKILL.md)

To link these repo-local skills into Codex's global skill directory, run:

```bash
bash scripts/sync_repo_skills_to_codex.sh
```

Then restart Codex.

## Learned Lessons

Durable lessons now live under [references/lessons](/Users/steve.spivak/Documents/MAcosAutomation/references/lessons).

Create a new lesson file with:

```bash
bash scripts/new_lesson.sh <area> <slug>
```
