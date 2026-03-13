# stage skill research before packaging

Date: 2026-03-13
Area: workflow
Status: validated

## Context

The repo started adding broader reusable Codex skills beyond CRA-specific work, using a local organizer JSON and external skill references as inputs.

## Trigger

There was a risk of turning source inspiration directly into final skills without a visible distillation step, which would make overlap, scope, and packaging quality harder to judge later.

## What Happened

A staged pipeline was created under `references/skill-research/wave-1/`:

- source distillation
- cluster mapping
- skill candidate mapping
- research gaps
- final skill specs

That staging made it easier to filter out weak candidates, defer narrow reviewer skills, and explain why the first wave focused on research, workflow, structure, and reasoning.

## Lesson

When growing the skill set from multiple sources, stage the research first and package the skills second. The distillation and candidate map are not overhead; they are what keep the skill library coherent.

## Evidence

- the organizer blueprint explicitly required distillation before final skill specs
- the staged artifacts made overlap and deferral decisions explicit
- the final wave stayed focused instead of importing every candidate family from the organizer

## Decision

Keep organizer-driven skill growth under `references/skill-research/` and require staged research artifacts before future multi-skill waves are packaged.

## Follow-Up

- keep later skill waves under the same staged research structure
- use `research-critique`, `structure-designer`, and `skill-refiner` to challenge future bundles before packaging

## Related Skills

- `repo-researcher`
- `research-synthesizer`
- `research-critique`
- `implementation-planner`
- `skill-refiner`
