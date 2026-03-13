---
name: cra-upstream-integration
description: Evaluate upstream Remodex package fit, identify supported extension points, separate wrap-from-fork decisions, and define upgrade policy. Use when the task involves third-party bridge integration strategy rather than direct feature implementation.
---

# CRA Upstream Integration

## Purpose

Prevents CRA from repeating premature custom-bridge work by forcing an explicit wrap-vs-fork evaluation around the upstream Remodex package.

## When To Use

- deciding whether CRA should wrap or fork upstream behavior
- evaluating upstream env vars, state paths, and extension points
- documenting hard-coded assumptions in the upstream package
- defining upgrade and compatibility policy

## Process

1. Read the upstream README and installed package behavior.
2. Separate proven behavior from assumptions.
3. Identify what CRA already gets for free from upstream.
4. Identify which missing requirements can be wrapped without a fork.
5. Recommend a fork only when a hard requirement cannot be met otherwise.

## Output Format

- Upstream capability summary
- Supported extension points
- Required CRA wrapper surfaces
- Fork gate recommendation
- Upgrade or drift risks
