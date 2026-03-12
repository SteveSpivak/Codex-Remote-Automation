---
name: cra-backend-developer
description: Build the local CRA broker, App Server approval handling, transcript normalization, replay fixtures, and notification payload construction. Use when the task involves protocol handling, broker logic, or approval-contract processing.
---

# CRA Backend / Broker Developer

## Purpose

Owns the primary CRA control plane: consuming Codex App Server approval events, normalizing them into a stable mobile-safe contract, recording transcripts, and resolving decisions back to Codex.

## When to Use

- App Server JSON-RPC handling over `stdio` or WebSocket
- Approval request normalization using `request_id`, `thread_id`, `turn_id`, and `item_id`
- Decision response wiring (`accept`, `acceptForSession`, `decline`, `cancel`)
- Transcript capture and normalization
- `codex exec --json` replay fixtures and event-corpus tooling
- Sanitized payload construction for the mobile approval surface

## Process

1. Validate the live surface with `codex app-server --help` and `codex exec --json`
2. Freeze the canonical request and response envelopes from [`references/output-contracts.md`](../../references/output-contracts.md)
3. Implement the broker adapter that maps App Server approval requests into the CRA request contract
4. Record both the raw protocol event and the sanitized mobile payload
5. Implement decision resolution by `request_id`
6. Build replay fixtures and contract tests before any mobile integration is considered complete

## Canonical Request Fields

- `request_id`
- `thread_id`
- `turn_id`
- `item_id`
- `kind`
- `summary`
- `available_decisions`
- `timestamp`

## Standards

- Treat App Server approval events as the source of truth
- Preserve `thread_id`, `turn_id`, and `item_id` alongside `request_id`
- Sanitize all operator-facing strings before they leave the broker
- Prefer replay fixtures over synthetic log parsing
- Label fallback prototype code that still uses `action_id` as fallback only

## Anti-Patterns

- Inferring approvals from logs when App Server approval requests are available
- Creating a second response identifier instead of using `request_id`
- Dropping raw protocol context from audit records
- Making notification-provider payloads the canonical schema

## Output Format

Produce:
- Broker module or protocol adapter shape
- Contract mapping notes for request and response fields
- Replay fixture or transcript strategy
- Tests for normalization, stale-request handling, and decision routing
- Performance notes for idle and active broker behavior
