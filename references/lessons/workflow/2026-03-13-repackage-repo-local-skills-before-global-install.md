# repackage repo-local skills before global install

Date: 2026-03-13
Area: workflow
Status: validated

## Context

Skills were discovered in another local repo under `skills-source/`, and the goal was to make them available as global Codex skills on this machine.

## Trigger

The source skills were useful, but they were written as repo-local wrappers. They pointed at external `docs/*` and `agents/*` files and did not include `agents/openai.yaml`.

## What Happened

The imported SPFx skill family was reviewed before installation. The two source repos contained duplicate, byte-identical skill files, so only one real source set needed evaluation. Those skills were then rewritten into portable forms inside this repo with:

- stronger trigger descriptions
- self-contained skill bodies
- `agents/openai.yaml`
- routing entries in `AGENTS.md`

## Lesson

Repo-local skills should not be installed globally as raw copies. First repackage them so they are portable, picker-friendly, and self-sufficient enough to work outside the original repo.

## Evidence

- the source SPFx skills were duplicated across two repos but identical
- they had no `agents/openai.yaml`
- their `Read first` sections depended on repo-level files outside the skill folders
- the cleaned-up versions installed cleanly into `~/.codex/skills`

## Decision

Treat external or repo-local skill sets as import candidates, not drop-in global skills. Preserve their core job, but rewrite packaging and trigger guidance before syncing them into Codex.

## Follow-Up

- use `skill-refiner` when importing future skill sets
- add an import assessment note whenever a source skill family is copied into this repo
- prefer one canonical imported copy even if multiple repos contain duplicates

## Related Skills

- `repo-researcher`
- `skill-refiner`
- `structure-designer`
