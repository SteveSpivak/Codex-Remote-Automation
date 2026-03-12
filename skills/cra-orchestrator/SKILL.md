---
name: cra-orchestrator
description: Route CRA (Codex Remote Automation) requests to the right specialist skill and assemble final deliverables. Use when the task spans multiple CRA subsystems or when the next specialist is unclear.
---

# CRA Orchestrator

## Purpose

Classifies CRA requests, selects the correct specialist skill, sequences handoffs, and assembles coherent deliverables.

## Routing Matrix

- Network, Tailscale, SSH, VPN, MagicDNS, iOS connectivity → `cra-network-architect`
- macOS daemon, launchd, AppleScript, JXA, Accessibility, actuator → `cra-macos-engineer`
- Python watcher, log parsing, webhook, Pushcut/Pushover, payload → `cra-backend-developer`
- SSH hardening, ACLs, payload sanitization, key rotation, audit → `cra-security-specialist`
- End-to-end flow, multi-phase work, unclear routing → `cra-orchestrator` (sequence specialists)

## Standard Process

1. Classify the request against the routing matrix
2. If single-domain: hand off immediately to the correct specialist
3. If multi-domain or phase-spanning: sequence specialists in dependency order
   - Security foundation first (Phase 1)
   - Outbound trigger second (Phase 2)
   - iOS bridge third (Phase 3)
   - Actuator fourth (Phase 4)
   - QA last (Phase 5)
4. Assemble final output per [`references/output-contracts.md`](../../references/output-contracts.md)

## Shared Standards

All work must comply with:
- [`references/cra-charter.md`](../../references/cra-charter.md) — authoritative architecture and KPI targets
- [`references/cra-standards.md`](../../references/cra-standards.md)
- [`references/cra-anti-patterns.md`](../../references/cra-anti-patterns.md)

## Output Envelope

- Goal
- Recommended approach
- Files or artifacts created/changed
- Commands to run
- Risks and constraints
- Validation and next checks
