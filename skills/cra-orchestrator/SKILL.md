---
name: cra-orchestrator
description: Route CRA requests across upstream Remodex proof, CRA wrapper work, relay decision work, security review, and test evidence. Use when the task spans multiple CRA subsystems or when the next specialist is unclear.
---

# CRA Orchestrator

## Purpose

Classifies CRA requests, selects the correct specialist skill, and sequences work around the upstream-first strategy.

## Hard Rule

Do not reimplement bridge or relay behavior until upstream `remodex up` has completed a known-good phone pairing for the target environment.

## Routing Matrix

- Third-party package fit, extension points, wrap-vs-fork decision, upgrade policy -> `cra-upstream-integration`
- CRA wrappers around upstream outputs, approval audit, policy adapters, transcript handling, replay fixtures -> `cra-backend-developer`
- Remodex install, env vars, `HOME` or state handling, local runtime commands, launchd, `.codex`, fallback tooling -> `cra-macos-engineer`
- Hosted-vs-self-hosted relay, `ws://` vs `wss://`, iPhone reachability, LAN or off-network behavior -> `cra-network-architect`
- Trust boundaries, local state storage, relay blindness, hosted-vs-self-hosted risk, approval authenticity -> `cra-security-specialist`
- Upstream proof matrix, reconnect checks, KPI evidence, fallback reliability validation -> `cra-test-engineer`

## Standard Process

1. Prove the upstream path first.
2. Route wrapper or audit work only after the proof status is known.
3. Route relay-fork work only if upstream proof exposes a real blocker.
4. Keep fallback tooling explicitly secondary.
5. Assemble output per [`references/output-contracts.md`](../../references/output-contracts.md).

## Shared Standards

All work must comply with:
- [`references/cra-charter.md`](../../references/cra-charter.md)
- [`references/cra-standards.md`](../../references/cra-standards.md)
- [`references/cra-anti-patterns.md`](../../references/cra-anti-patterns.md)
- [`references/research/remodex-upstream-assessment.md`](../../references/research/remodex-upstream-assessment.md)

## Output Envelope

- Goal
- Upstream proof status
- Wrapper or fork path
- Fallback path, if any
- Commands or checks run
- Risks and constraints
- Validation and next checks
