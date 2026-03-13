---
name: evidence-collector
description: Gather the minimum high-signal logs, state files, commands, and artifacts needed to prove or disprove a diagnosis. Use when debugging intermittent issues, integration failures, reconnect loops, launchd problems, or environment-specific behavior.
---

# Evidence Collector

## Purpose

Collects a compact, decision-grade evidence set instead of broad, noisy dumps.

## When To Use

- Reconnect or retry loops
- Authentication or state drift
- LaunchAgent or background runtime failures
- Upstream integration issues with unclear root cause
- Any problem where stale logs could be confused with live behavior

## Process

1. Define the hypothesis being tested.
2. Choose the smallest evidence set that can confirm or refute it.
3. Prefer these sources in order:
   - live process output
   - current state files
   - config or environment
   - direct protocol or transport probe
   - older logs only for historical context
4. Label each artifact as live, stale, or derived.
5. Report only the facts that move the decision.

## Evidence Checklist

- Exact command or entrypoint used
- Current state file contents, if relevant
- Current config or environment variables, if relevant
- Tail of the active stdout or stderr logs
- One direct probe of the failing boundary when possible

## Hard Rules

- Do not dump entire logs when the last useful section is enough.
- Do not mix stale and live evidence without labeling it.
- Do not claim causality from correlation alone.
- Keep the evidence chain reproducible.

## Deliverables

- Hypothesis under test
- Artifacts gathered and why
- Facts established
- Ambiguities or missing proof
- Recommended next probe

## Output Format

- Hypothesis
- Evidence collected
- Facts confirmed
- Still unknown
- Next probe
