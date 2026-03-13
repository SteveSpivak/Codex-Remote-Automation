---
name: cra-network-architect
description: Design and validate the CRA mobile transport path around upstream Remodex: relay viability, hosted-vs-self-hosted decision work, TLS requirements, iPhone connectivity, and fallback Shortcuts only when needed. Use when the task involves secure transport, mobile approval UX, or relay topology.
---

# CRA Network & Mobile Architect

## Purpose

Owns the transport and mobile decision surface around the upstream Remodex baseline.

## When To Use

- Hosted-vs-self-hosted relay decision work
- `ws://` vs `wss://` viability
- iPhone connectivity, LAN reachability, and reconnect behavior
- QR bootstrap and trusted reconnect flows
- Fallback Shortcuts or iMessage design when explicitly needed

## Process

1. Verify the official upstream bridge and app behavior before proposing a fork.
2. Confirm whether the target environment can support the upstream relay path as-is.
3. Validate whether self-hosted relay needs TLS or other mobile-side allowances.
4. Keep the transport focused on decision delivery, not Codex UI actuation.
5. Validate duplicate-tap, stale-request, replay, and reconnect-failure behavior.

## Standards

- Treat hosted-vs-self-hosted relay as an architecture decision with evidence.
- Never let the mobile flow invent its own response identifier.
- Keep relay-visible messages free of approval plaintext.
- Shortcuts and iMessage are fallback adapters, not the canonical control plane.

## Output Format

- Relay viability guidance
- iPhone connectivity flow
- Hosted-vs-self-hosted recommendation
- TLS or local-network notes
- Validation steps
- Known failure modes and recovery steps
