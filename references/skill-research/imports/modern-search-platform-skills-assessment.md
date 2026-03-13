# Modern Search Platform Skills Assessment

## Source

- `/Users/steve.spivak/Documents/scripts/modern-search-platform/skills-source`
- `/Users/steve.spivak/Documents/scripts/modern-search-platform-metadata-picker-fix/skills-source`

## Findings

- The five SPFx skill folders are duplicated across both repos and are byte-identical.
- The source skills are worth importing because they have clear boundaries:
  - `spfx-architect`
  - `spfx-component-creator`
  - `spfx-orchestrator`
  - `spfx-qa`
  - `spfx-reviewer`
- They are not strong global Codex skills as-is because:
  - they do not include `agents/openai.yaml`
  - their `Read first` instructions reference repo-level docs outside the skill folder
  - they are packaged as repo-local wrappers, not portable skills

## Import Decision

Import all five, but update them first.

## Required Updates

- Add `agents/openai.yaml` for Codex picker friendliness.
- Rewrite `Read first` guidance so it works in arbitrary SPFx repos:
  - prefer local `docs/ARCHITECTURE.md`, `docs/BUILD.md`, `agents/AGENTS.md`, and repo rules if present
  - otherwise fall back to general SPFx and Microsoft 365 architecture reasoning
- Keep the original role boundaries and output contracts.
- Preserve the architecture -> implementation -> review -> QA split and the thin orchestrator model.

## Non-Goals

- Do not copy repo-specific internal paths as hard requirements.
- Do not bundle the full `modern-search-platform` docs into these skills unless a later task needs progressive-disclosure references.
