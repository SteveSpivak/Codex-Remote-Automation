---
name: cra-network-architect
description: Design and implement the CRA bridge transport path: self-hosted relay, native iPhone client connectivity, pairing and reconnect UX, and fallback Shortcuts only when needed. Use when the task involves secure transport, mobile approval UX, or relay topology.
---

# CRA Network & Mobile Architect

## Purpose

Owns the secure bridge between the iPhone approval surface and the local CRA Bridge: self-hosted relay topology, native iOS client connectivity, pairing and reconnect UX, and fallback Shortcuts only when needed.

## When to Use

- Self-hosted relay topology, endpoint shape, TLS or local-network placement
- Native iOS client connectivity to the relay
- QR bootstrap and trusted reconnect flows
- Private decision return path from iPhone to bridge
- Fallback Shortcut construction around `request_id` and `decision`
- Network drop handling, reconnect logic, and cellular/Wi-Fi transitions

## Process

1. Verify the bridge-side destination before designing the mobile flow
2. Confirm the relay is transport-only and does not need approval plaintext
3. Design pairing, reconnect, and pending snapshot behavior before UI polish
4. Build the native iOS client around the canonical request and response contracts
5. Keep the transport focused on decision delivery, not direct Codex UI actuation
6. Validate duplicate-tap, stale-request, replay, and reconnect-failure behavior

## Standards

- Never use router port forwarding or a managed relay as the canonical bridge path
- Never let the mobile flow invent its own response identifier
- Keep relay-visible messages free of approval plaintext
- The native client must handle reconnect and stale-request failures explicitly
- Shortcuts and iMessage are fallback adapters, not the canonical control plane

## Anti-Patterns

- Designing the mobile path around desktop-button clicks
- Treating the relay as a business-logic service instead of a transport-only hop
- Testing only on a perfect local network with no reconnect scenarios
- Hardcoding the Mac's local IP address into the long-term architecture

## Output Format

Produce:
- Relay or private-transport guidance
- Native iOS client flow using `request_id` and `decision`
- Pairing and reconnect notes
- Fallback Shortcut or iMessage note when applicable
- Off-network or relay validation steps
- Known failure modes and recovery steps
