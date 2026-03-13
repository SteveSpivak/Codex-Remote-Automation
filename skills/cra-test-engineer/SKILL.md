---
name: cra-test-engineer
description: Design and run CRA proof matrices for upstream Remodex, reconnect tests, approval decision matrices, resilience exercises, and KPI reporting. Use when the task involves proving the mobile approval flow works reliably.
---

# CRA Test Engineer

## Purpose

Owns verification of the CRA system with the upstream Remodex baseline first and fallback paths second.

## When To Use

- Upstream bridge startup checks
- QR scan and phone-pairing proof
- Relay connectivity and reconnect tests
- App Server approval transcript replay
- Approval decision matrix testing
- Duplicate, stale-request, replay, timeout, and network-drop tests

## Process

1. Start with the upstream proof matrix before any fork work.
2. Validate the request and response contracts before relay changes.
3. Exercise pairing, reconnect, and replay-rejection cases before end-to-end approval UX is called ready.
4. Measure component timings separately, then end-to-end timings.
5. Report fallback reliability separately from the primary path.

## Required Proof Matrix

- upstream bridge starts
- QR scans
- phone pairs
- relay stays connected
- approval request arrives
- decision returns
- reconnect works

## Output Format

- Proof matrix and commands
- Evidence paths or captured output
- Findings grouped by severity
- Release recommendation: ready, ready with conditions, or blocked
