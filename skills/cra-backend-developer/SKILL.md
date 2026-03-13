---
name: cra-backend-developer
description: Build CRA wrappers around upstream Remodex and Codex App Server outputs, including approval audit, policy adapters, transcript normalization, and replay fixtures. Use when the task involves protocol handling, wrapper logic, or approval-contract processing.
---

# CRA Backend / Wrapper Developer

## Purpose

Owns CRA behavior that sits around the upstream Remodex baseline: audit, policy, transcript capture, replay fixtures, and approval-contract normalization.

## When To Use

- Wrapping upstream bridge outputs without replacing the bridge
- App Server approval normalization using `request_id`, `thread_id`, `turn_id`, and `item_id`
- Audit records, transcript capture, and replay fixtures
- CRA-local policy checks around approvals
- Decision routing validation after upstream proof exists

## Process

1. Validate the live surface with `codex app-server --help` and `codex exec --json`.
2. Confirm the upstream Remodex baseline is either proven or explicitly blocked.
3. Freeze the canonical request and response envelopes from [`references/output-contracts.md`](../../references/output-contracts.md).
4. Implement the thinnest CRA adapter that maps upstream and App Server events into the CRA request contract.
5. Record both the raw protocol event and the sanitized mobile payload.
6. Build replay fixtures and contract tests before mobile integration is called complete.

## Standards

- Treat App Server approval events as the source of truth.
- Preserve `thread_id`, `turn_id`, and `item_id` alongside `request_id`.
- Sanitize all operator-facing strings before they leave the wrapper.
- Prefer replay fixtures over synthetic log parsing.
- Do not fork bridge or relay behavior from this skill unless the fork gate has been explicitly crossed.

## Output Format

- Wrapper shape
- Contract mapping notes
- Audit and transcript strategy
- Replay strategy
- Tests for normalization, stale-request handling, replay rejection, and decision routing
