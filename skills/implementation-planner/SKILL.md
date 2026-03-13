---
name: implementation-planner
description: Convert intent into a decision-complete implementation plan. Use when the user needs staged work, interfaces, defaults, assumptions, constraints, or a test plan before coding or rollout.
---

# Implementation Planner

## Purpose

Produce plans that are concrete enough to build against, not just discuss.

## Process

1. State the target outcome and the success boundary.
2. Lock the interfaces, contracts, and defaults that the plan depends on.
3. Sequence the work in risk-first order.
4. Identify assumptions, blockers, and decision gates.
5. Attach the tests needed to prove each stage.

## Hard Rules

- Plans must name interfaces, defaults, and tests.
- Put the highest-risk unknowns first.
- Distinguish implementation work from later hardening work.
- If a plan depends on external research or operator setup, say so explicitly.

## Deliverables

- Summary
- Key changes
- Interfaces and defaults
- Test plan
- Assumptions and blockers

## Output Format

- Summary
- Implementation steps
- Contracts and defaults
- Tests
- Assumptions
