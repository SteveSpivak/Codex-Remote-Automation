---
name: persistent-debugger
description: Drive iterative bug hunting with reproduction, hypothesis tracking, proof loops, and narrow next checks. Use when a failure needs disciplined debugging rather than a one-shot guess.
---

# Persistent Debugger

## Purpose

Keep debugging loops focused until the root cause is narrowed or the blocker is explicit.

## Process

1. Define the current failure and the desired success condition.
2. Reproduce the issue with the smallest reliable command or action.
3. Record the active hypothesis and the next falsifying check.
4. Update the hypothesis log after every probe.
5. Stop when the root cause, environmental blocker, or remaining uncertainty is clear.

## Hard Rules

- Never debug from memory when a repro is available.
- One hypothesis and one next proof per loop.
- Prefer narrowing over broad logging sprees.
- Label fixes as proven, plausible, or blocked.

## Deliverables

- Repro status
- Hypothesis log
- Facts established
- Root cause or blocker
- Next proof command

## Output Format

- Failure under test
- Current repro
- Hypothesis log
- What is proven now
- Next check
