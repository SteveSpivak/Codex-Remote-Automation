---
name: spfx-component-creator
description: Implement SPFx web parts, extensions, services, packages, manifests, and supporting TypeScript or React code. Use when the user needs concrete SPFx implementation help, file structure, build steps, or repo-aware code changes.
---

# SPFx Component Creator

## Purpose

Build SPFx implementation artifacts without collapsing architecture and packaging discipline.

## Process

1. Read the target repo's build, architecture, and local rules if they exist.
2. Locate the host app, shared packages, and build entrypoints before editing.
3. Keep shared logic in shared packages when the repo has that boundary.
4. Implement the smallest correct change set with commands and follow-up checks.
5. Report known limitations and build impact explicitly.

## Preferred Inputs

If present in the target repo, read these first:
- `docs/BUILD.md`
- `docs/ARCHITECTURE.md`
- `agents/AGENTS.md`
- local standards, anti-patterns, or output contracts

## Hard Rules

- Do not move shared logic into the SPFx app without justification.
- Include commands to build, test, or run when structure or manifests change.
- Respect the current SPFx-supported dependency model unless the user explicitly accepts risk.
- Keep output concrete: files, code, commands, limitations.

## Deliverables

- File tree or changed files
- Code or scaffolding
- Configuration notes
- Commands to run
- Known limitations and follow-up checks

## Output Format

- Files created or changed
- Code
- Configuration notes
- Commands
- Limitations
