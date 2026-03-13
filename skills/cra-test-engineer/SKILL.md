---
name: cra-test-engineer
description: Design and run CRA replay tests, bridge reconnect tests, approval decision matrices, resilience exercises, and KPI reporting. Use when the task involves proving the bridge-first flow works reliably before or after production wiring.
---

# CRA Test Engineer

## Purpose

Owns verification of the Codex Remote Automation system: replay fixtures, bridge protocol checks, reconnect testing, KPI evidence, and fallback reliability checks when fallback tooling is in scope.

## When to Use

- App Server approval transcript replay
- Bridge pairing, reconnect, and encrypted-envelope tests
- `codex exec --json` fixture generation and validation
- Approval decision matrix testing (`accept`, `acceptForSession`, `decline`, `cancel`)
- Duplicate, stale-request, replay, timeout, and network-drop tests
- Long-horizon validation loops and KPI reporting
- Fallback path reliability checks for Accessibility or OCR

## Process

1. Start with protocol fixtures and replay before live mobile tests
2. Validate the request and response contracts before relay integration
3. Exercise pairing, reconnect, and replay-rejection cases before end-to-end approval UX
4. Measure component timings separately, then end-to-end timings
5. Exercise resilience scenarios: duplicate decisions, stale `request_id`, relay drop, sleep/wake, revoked permissions
6. Produce a concise KPI report and release recommendation

## Standards

- Replay coverage is mandatory before live approval testing
- Every test run must record timestamps, request identifiers, expected decisions, and observed outcomes
- KPI reporting must distinguish bridge-path timing from fallback-path timing
- Reconnect tests must verify pending approval catch-up and stale-decision rejection
- Fallback reliability must be reported separately from the primary path

## Anti-Patterns

- Waiting for live approvals before building a replay corpus
- Calling the system ready without a decision-matrix test
- Calling the bridge ready without a reconnect or replay-rejection test
- Treating fallback OCR success as proof that the primary path is healthy

## Output Format

Produce:
- Replay commands and fixtures
- Test matrix: contract, replay, bridge reconnect, integration, resilience, KPI, fallback
- Evidence log paths or captured output
- Findings grouped by severity
- Release recommendation: ready, ready with conditions, or blocked
