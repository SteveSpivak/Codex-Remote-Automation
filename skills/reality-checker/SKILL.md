---
name: reality-checker
description: Stress-test technical assumptions, separate confirmed evidence from guesses, and stop premature rewrites or pivots. Use when a diagnosis may be confusing environment issues with code defects, or when a fork, workaround, or architecture change is being considered.
---

# Reality Checker

## Purpose

Prevents avoidable rework by forcing evidence before major conclusions.

## When To Use

- An implementation path keeps changing without a clean proof
- A failure could be caused by code, environment, policy, or upstream behavior
- A fork, rewrite, or architectural pivot is being proposed
- A "probably" explanation is driving decisions without a falsifying check

## Process

1. State the current claim in one sentence.
2. Separate facts, inferences, and unknowns.
3. Identify the cheapest test that could disprove the claim.
4. Classify the blocker as one of:
   - code defect
   - environment or policy constraint
   - upstream package behavior
   - operator error or missing setup
5. Recommend continue, wrap, fork, or stop only after that classification is supported.

## Hard Rules

- Do not accept "it should work" as evidence.
- Prefer direct logs, process output, state files, and protocol traces over interpretation.
- If the cheapest falsifying test has not been run, say that the conclusion is provisional.
- If the problem is environmental, say so explicitly and stop blaming the repo.

## Deliverables

- Current claim
- Confirmed facts
- Unknowns and assumptions
- Cheapest falsifying test
- Blocker classification
- Recommendation: continue, wrap, fork, or stop

## Output Format

- Claim under test
- Evidence summary
- What is still unproven
- Decision and rationale
- Next validating check
