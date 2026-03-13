# CRA Repo Guidance

## Source Of Truth

- Treat [references/cra-charter.md](references/cra-charter.md) as the primary architecture document.
- Treat [references/output-contracts.md](references/output-contracts.md) as the canonical request and response contract source.
- Treat the existing `cra/`, `scripts/`, and `references/discovery/` hybrid-native artifacts as fallback or discovery tooling unless the task explicitly says otherwise.

## Architecture Preference

- Use `codex app-server` as the primary approval surface.
- Use the warm CRA Bridge plus self-hosted relay plus native iOS CRA Operator app as the primary operator path.
- Use `codex exec --json` for replay, fixtures, and long-horizon validation.
- Use iPhone Shortcuts or iMessage only as fallback/dev tooling while the native iOS app is incomplete.
- Only drop to Accessibility, AppleScript, OCR, or screenshot targeting if:
  - the task is explicitly about fallback tooling, or
  - the App Server path is blocked and the fallback label is kept explicit.

## Working Pattern

For CRA work, prefer this loop:

1. Plan the protocol, contract, or transport change
2. Implement the smallest useful slice
3. Verify with Codex help output, replay fixtures, tests, or local checks
4. Repair drift or failed assumptions
5. Report the primary path, fallback status, and evidence

## Skill Routing

- Use `cra-orchestrator` for cross-domain or architecture work
- Use `cra-backend-developer` for bridge runtime, JSON-RPC, transcript, and replay work
- Use `cra-macos-engineer` for `.codex`, App Server lifecycle, bridge residency, QR artifacts, and fallback tooling
- Use `cra-network-architect` for relay transport, native iOS client integration, fallback Shortcuts, and mobile connectivity
- Use `cra-security-specialist` for pairing, replay protection, transport hardening, and threat modeling
- Use `cra-test-engineer` for replay, reconnect, KPI, and fallback reliability validation

## Repo-Native Codex Surfaces

- Shared project config lives in `.codex/config.toml`
- Shared repo commands live in `.codex/commands/`
- Recurring health or replay work should prefer Codex automations and Triage before a custom scheduler is added

## Fallback Rules

- When fallback tooling is used, say so explicitly in the plan, implementation notes, and final report.
- Do not describe Shortcuts, iMessage, `action_id`, `AXDescription`, AppleScript, or OCR as the primary CRA contract after the bridge pivot.
