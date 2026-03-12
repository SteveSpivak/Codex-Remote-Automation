---
name: cra-network-architect
description: Design and implement the private iPhone-to-broker decision path for CRA: Tailscale, SSH, iOS Shortcuts, and optional notification adapters. Use when the task involves secure transport, mobile approval UX, or off-network connectivity.
---

# CRA Network & Mobile Architect

## Purpose

Owns the secure bridge between the iPhone approval surface and the local CRA broker: Tailscale configuration, private decision transport, iOS Shortcuts logic, and optional notification adapters.

## When to Use

- Tailscale setup, peer discovery, MagicDNS configuration
- Private decision return path from iPhone to broker
- iOS Shortcut construction around `request_id` and `decision`
- Optional notification adapter evaluation, including Pushcut or Pushover, when needed for operator UX
- Network drop handling, VPN reconnect logic, cellular/Wi-Fi transitions

## Process

1. Verify the broker-side destination before designing the mobile flow
2. Confirm private connectivity from the iPhone to the Mac off-network
3. Build the Shortcut around the canonical request and response contracts
4. Keep the transport focused on decision delivery, not direct Codex UI actuation
5. Validate duplicate-tap, stale-request, and VPN-unavailable behavior

## Standards

- Never use DDNS or router port forwarding
- Never let the mobile flow invent its own response identifier
- The Shortcut must handle VPN-not-connected and stale-request failures explicitly
- Third-party notification services are optional adapters, not the canonical control plane

## Anti-Patterns

- Designing the Shortcut around desktop-button clicks
- Testing only on local Wi-Fi
- Hardcoding the Mac's local IP address instead of using a private, stable route

## Output Format

Produce:
- Tailscale or private-transport guidance
- iOS Shortcut description using `request_id` and `decision`
- Response delivery command shape or transport note
- Off-network validation steps
- Known failure modes and recovery steps
