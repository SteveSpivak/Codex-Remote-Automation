# CRA Standards

These standards apply to all Codex Remote Automation (CRA) planning and implementation work.

## Architecture Invariants

- Preserve the canonical topology: `codex app-server` -> CRA broker -> iPhone approval surface -> broker decision response -> Codex.
- Keep the project human-in-the-loop. CRA may assist approval flow, but it must not bypass the human decision.
- Prefer protocol surfaces before UI surfaces. App Server and noninteractive transcript flows come before Accessibility, AppleScript, or OCR.
- Treat the project as remote approval for Codex only, not as a general-purpose macOS remote control framework.

## Security Baseline

- Do not expose the Mac to the public internet. Remote access must stay inside Tailscale or an equivalently private channel.
- Use key-only SSH with Ed25519 keys and disable password authentication and root login when SSH is part of the mobile decision path.
- Sanitize every operator-visible or transport-visible string before it is serialized, logged, or shown on the phone.
- Use the App Server `request_id` as the canonical response handle and treat it as untrusted input everywhere else in the system.

## Implementation Rules

- Prefer App Server approval requests and `codex exec --json` fixtures over log scraping or UI inference.
- Preserve `thread_id`, `turn_id`, and `item_id` alongside `request_id` for audit, replay, and debugging.
- Keep repo-native Codex guidance in version control: `AGENTS.md`, `.codex/config.toml`, and `.codex/commands/`.
- Label Accessibility, AppleScript, OCR, and `action_id`-based flows as fallback or discovery only.
- Keep launchd-managed or broker-managed components restartable and observable with explicit log targets.

## Performance and Reliability Targets

- Outbound notification latency target: less than 2 seconds from App Server request to phone-visible prompt.
- Inbound approval latency target: less than 500 ms P95 from tap to broker response.
- Idle broker overhead target: less than 1% CPU and less than 50 MB RAM.
- Design recovery for sleep/wake transitions, network changes, revoked permissions, and stale approval requests.

## Documentation Expectations

- Every subsystem deliverable must include validation steps, known failure modes, and recovery guidance.
- Security-sensitive changes must include a short risk note, even when the change is narrow.
- When fallback tooling is discussed, the fallback label must be explicit.
- Recurring health or replay checks should prefer Codex automations and Triage before adding a custom scheduler.
