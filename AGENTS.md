# CRA Repo Guidance

## Source Of Truth

- Treat [references/cra-charter.md](references/cra-charter.md) as the primary architecture document.
- Treat [references/output-contracts.md](references/output-contracts.md) as the canonical request and response contract source.
- Treat [references/research/remodex-upstream-assessment.md](references/research/remodex-upstream-assessment.md) as the current upstream evidence file.
- Treat the existing `cra/`, `scripts/`, `references/discovery/`, and `remodex/` compatibility-study artifacts as fallback, research, or wrapper material unless the task explicitly says otherwise.

## Architecture Preference

- Use the official `remodex` package as the primary mobile bridge baseline.
- Do not reimplement bridge or relay behavior until upstream `remodex up` has completed a known-good phone pairing for the target environment.
- Use `codex app-server` as the Codex-side approval surface and `codex exec --json` for replay and fixtures.
- Use Shortcuts, iMessage, Accessibility, AppleScript, or OCR only as fallback or discovery tooling.
- If upstream Remodex cannot satisfy a hard requirement, fork the minimum surface necessary and document the evidence that forced the fork.

## Working Pattern

For CRA work, prefer this loop:

1. Verify the upstream package behavior and target constraints
2. Wrap or adapt the smallest useful surface
3. Verify with help output, replay fixtures, tests, or local checks
4. Repair drift or failed assumptions
5. Report the upstream path, fallback status, and evidence

## Skill Routing

- Use `cra-orchestrator` for cross-domain or architecture work
- Use `cra-upstream-integration` for third-party package fit, extension-point review, and wrap-vs-fork decisions
- Use `cra-backend-developer` for CRA wrappers around upstream outputs, approval audit, policy, transcript, and replay work
- Use `cra-macos-engineer` for Remodex install, env vars, local state, launchd, `.codex`, and fallback tooling
- Use `cra-network-architect` for relay transport, hosted-vs-self-hosted decision work, TLS, and iPhone connectivity
- Use `cra-security-specialist` for trust boundaries, pairing storage, relay blindness, and hosted-vs-self-hosted risk
- Use `cra-test-engineer` for upstream proof matrices, reconnect checks, KPI evidence, and fallback reliability validation

## Repo-Native Codex Surfaces

- Shared project config lives in `.codex/config.toml`
- Shared repo commands live in `.codex/commands/`
- Recurring health or replay work should prefer Codex automations and Triage before a custom scheduler is added
- Repo-local CRA skills can be linked into `$CODEX_HOME/skills` with `bash scripts/sync_repo_skills_to_codex.sh`
- Durable lessons live under `references/lessons/` and should be captured when a finding changes architecture, skills, or workflow

## Fallback Rules

- When fallback tooling is used, say so explicitly in the plan, implementation notes, and final report.
- Do not describe the in-repo `remodex/` compatibility study, Shortcuts, iMessage, `action_id`, `AXDescription`, AppleScript, or OCR as the primary CRA contract.
