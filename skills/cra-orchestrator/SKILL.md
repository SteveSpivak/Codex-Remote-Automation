---
name: cra-orchestrator
description: Route CRA (Codex Remote Automation) requests to the right specialist skill and assemble final deliverables. Use when the task spans multiple CRA subsystems or when the next specialist is unclear.
---

# CRA Orchestrator

## Purpose

Classifies CRA requests, selects the correct specialist skill, sequences handoffs, and assembles coherent deliverables around the bridge-first architecture.

## Routing Matrix

- App Server protocol, warm bridge runtime, JSON-RPC approvals, reconnect snapshots, noninteractive replay -> `cra-backend-developer`
- `.codex` project config, App Server lifecycle, bridge residency, QR artifacts, launchd support, fallback Accessibility or OCR tooling -> `cra-macos-engineer`
- Self-hosted relay, native iOS operator client, pairing/reconnect UX, fallback Shortcuts or iMessage transport -> `cra-network-architect`
- Threat model, pairing and reconnect hardening, transcript integrity, relay blindness, key rotation -> `cra-security-specialist`
- Replay suites, KPI evidence, reconnect checks, fallback reliability validation -> `cra-test-engineer`
- Cross-skill sequencing, architecture changes, mixed protocol and mobile work -> `cra-orchestrator`

## Standard Process

1. Confirm the primary path is `bridge_secure_session`, not Shortcut-only glue or UI automation
2. Route the core broker or contract work first
3. Sequence supporting work in dependency order:
   - contract and protocol alignment
   - bridge runtime and local Codex environment guidance
   - relay, pairing, and mobile transport
   - security and replay protection
   - fallback tooling only if the primary path is blocked or explicitly requested
   - replay and QA last
4. Assemble final output per [`references/output-contracts.md`](../../references/output-contracts.md)

## Shared Standards

All work must comply with:
- [`references/cra-charter.md`](../../references/cra-charter.md) — authoritative architecture and KPI targets
- [`references/cra-standards.md`](../../references/cra-standards.md)
- [`references/cra-anti-patterns.md`](../../references/cra-anti-patterns.md)

## Thinking Pattern

For long-horizon CRA work, prefer this loop:

1. Plan the protocol or contract change
2. Implement the smallest useful slice
3. Verify with App Server help, relay checks, replay, tests, or local checks
4. Repair drift or failed assumptions
5. Report the primary path, fallback status, and evidence

## Output Envelope

- Goal
- Primary protocol path
- Fallback path, if any
- Files or artifacts created or changed
- Commands or checks run
- Risks and constraints
- Validation and next checks
