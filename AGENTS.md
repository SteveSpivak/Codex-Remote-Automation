# CRA Repo Guidance

## Source Of Truth

- Treat [references/cra-charter.md](references/cra-charter.md) as the primary architecture document.
- Treat [references/output-contracts.md](references/output-contracts.md) as the canonical request and response contract source.
- Treat [references/research/remodex-upstream-assessment.md](references/research/remodex-upstream-assessment.md) as the current upstream evidence file.
- Treat [references/skill-research/](references/skill-research/) as the staging area for organizer-driven skill research, distillation, and wave planning.
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
- Use `reality-checker` when a diagnosis, rewrite, or pivot may be based on assumption rather than proof
- Use `evidence-collector` when a compact set of logs, state, and probes is needed to prove or disprove a claim
- Use `lesson-curator` when a durable finding should update `references/lessons/`, repo guidance, or skill behavior
- Use `repo-researcher` when a repo, architecture, or toolchain needs a fast source map before implementation or review
- Use `research-synthesizer` when multiple sources need to be turned into a decision memo rather than a stack of summaries
- Use `research-critique` when a source set may be stale, contradictory, hype-driven, or too weak to support a recommendation
- Use `implementation-planner` when intent needs to be turned into staged work with interfaces, defaults, and tests
- Use `persistent-debugger` when a failure needs iterative reproduction, hypothesis tracking, and proof loops
- Use `structure-designer` when a plan, prompt, doc, or architecture note is correct but poorly structured
- Use `thinking-coach` when reasoning quality, assumption checks, or tradeoff framing need improvement
- Use `skill-refiner` when an existing skill needs trigger cleanup, de-bloating, or packaging correction
- Use `spfx-orchestrator` for SPFx or Microsoft 365 extensibility work that spans architecture, implementation, review, QA, or unclear routing
- Use `spfx-architect` for SPFx architecture, permissions, API choice, dependency, and deployment decisions
- Use `spfx-component-creator` for concrete SPFx code, manifests, packages, and implementation changes
- Use `spfx-reviewer` for SPFx code review with SharePoint-specific risk awareness
- Use `spfx-qa` for SPFx validation strategy, regression planning, and release readiness

## Repo-Native Codex Surfaces

- Shared project config lives in `.codex/config.toml`
- Shared repo commands live in `.codex/commands/`
- Recurring health or replay work should prefer Codex automations and Triage before a custom scheduler is added
- Repo-local CRA skills can be linked into `$CODEX_HOME/skills` with `bash scripts/sync_repo_skills_to_codex.sh`
- Skill research outputs for staged waves live under `references/skill-research/`
- Durable lessons live under `references/lessons/` and should be captured when a finding changes architecture, skills, or workflow
- Meta-productivity skills should stay small, evidence-first, and reusable across projects rather than project-persona heavy

## Fallback Rules

- When fallback tooling is used, say so explicitly in the plan, implementation notes, and final report.
- Do not describe the in-repo `remodex/` compatibility study, Shortcuts, iMessage, `action_id`, `AXDescription`, AppleScript, or OCR as the primary CRA contract.
