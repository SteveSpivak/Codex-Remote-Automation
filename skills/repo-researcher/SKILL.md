---
name: repo-researcher
description: Map an unfamiliar repository, architecture, or toolchain quickly. Use when onboarding to a new codebase, locating entrypoints, identifying ownership boundaries, or building a next-read list before implementation or review.
---

# Repo Researcher

## Purpose

Build a fast, evidence-backed map of a repository before deeper work starts.

## Process

1. Identify the repo shape: entry files, package manifests, app boundaries, config roots, and test surfaces.
2. Find the likely execution path or feature path relevant to the request.
3. Separate confirmed structure from inferred structure.
4. Highlight the smallest set of files worth reading next.
5. Stop once the map is good enough to act without guessing.

## Hard Rules

- Prefer source maps and entrypoints over broad file dumps.
- Label uncertain ownership, runtime flow, or generated code explicitly.
- Do not pretend a repo is understood just because the top-level tree is known.
- Keep the next-read list short and high signal.

## Deliverables

- Repo snapshot
- Key entrypoints and boundaries
- Confirmed vs inferred architecture notes
- Important unknowns
- Next-read list

## Output Format

- Repo snapshot
- Entry points
- Important systems
- Unknowns
- Next reads
