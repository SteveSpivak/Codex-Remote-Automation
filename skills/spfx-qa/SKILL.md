---
name: spfx-qa
description: Create SPFx test plans, validation checklists, regression coverage, and release readiness guidance. Use when the user needs structured validation before shipping an SPFx or Microsoft 365 extensibility change.
---

# SPFx QA

## Purpose

Define release-readiness checks for SPFx work with a practical bias.

## Process

1. Identify the affected host surface, packages, and deployment path.
2. Read local build and architecture docs if they exist.
3. Build a test strategy around rendering, data, error handling, performance, accessibility, and deployment.
4. Separate manual tests, regression focus, and release gates.
5. Keep the checklist proportional to the change, not generic boilerplate.

## Coverage Areas

- rendering and host compatibility
- data loading and empty states
- error states and denied access behavior
- performance and responsiveness
- accessibility basics
- packaging, deployment, and upgrade validation

## Hard Rules

- Do not claim release readiness without naming the checks that prove it.
- Prefer targeted regression focus over generic testing sprawl.
- Make environment or tenant assumptions explicit.
- Keep the test strategy tied to the actual change surface.

## Deliverables

- Test strategy summary
- Manual test cases
- Regression matrix
- Release readiness checklist

## Output Format

- Test strategy
- Manual test cases
- Regression focus
- Release readiness checklist
