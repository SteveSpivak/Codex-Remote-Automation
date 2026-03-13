# CRA Standards

These standards apply to all Codex Remote Automation (CRA) planning and implementation work.

## Architecture Invariants

- Preserve the canonical approval contract based on `request_id`, `thread_id`, `turn_id`, and `item_id`.
- Prefer upstream `remodex` before custom bridge or relay ownership.
- Use `codex app-server` and `codex exec --json` before any UI inference or Shortcut-only glue.
- Keep the project human-in-the-loop. CRA may assist approval flow, but it must not bypass the human decision.
- Treat the project as remote approval for Codex only, not as a general-purpose macOS remote control framework.

## Upstream-First Rules

- Do not reimplement bridge or relay behavior until upstream `remodex up` has completed a known-good phone pairing for the target environment.
- Wrap upstream behavior thinly for audit, policy, and operator guidance before considering a fork.
- Fork only when a proven upstream limitation blocks a hard requirement.
- When research is incomplete, record the gap explicitly instead of implying that the self-hosted path is already production-ready.

## Security Baseline

- Treat hosted-vs-self-hosted relay choice as a security decision, not a styling preference.
- QR bootstrap payloads must expire quickly, trusted reconnect state must be bridge-side only, and the primary pairing material must match upstream Remodex identity-key behavior unless a fork is explicitly approved.
- Sanitize every operator-visible or transport-visible string before it is serialized, logged, or shown on the phone.
- Use the App Server `request_id` as the canonical response handle and treat it as untrusted input everywhere else in the system.
- Reject replayed or out-of-order encrypted envelopes.
- Use key-only SSH with Ed25519 keys and disable password authentication and root login when SSH is used for fallback decision return.

## Implementation Rules

- Preserve `thread_id`, `turn_id`, and `item_id` alongside `request_id` for audit, replay, and debugging.
- Keep repo-native Codex guidance in version control: `AGENTS.md`, `.codex/config.toml`, and `.codex/commands/`.
- Keep bridge device identity, trust state, and reconnect state explicit and inspectable.
- Label Shortcuts, iMessage, Accessibility, AppleScript, OCR, and `action_id`-based flows as fallback or discovery only.
- Label the in-repo `remodex/` implementation as a compatibility study unless it is explicitly promoted by evidence.

## Performance and Reliability Targets

- Outbound notification latency target: less than 2 seconds from App Server request to phone-visible prompt.
- Inbound approval latency target: less than 500 ms P95 from tap to broker response.
- Idle wrapper overhead target: less than 1% CPU and less than 50 MB RAM.
- Design recovery for sleep/wake transitions, relay reconnects, network changes, revoked permissions, and stale approval requests.

## Documentation Expectations

- Every subsystem deliverable must include validation steps, known failure modes, and recovery guidance.
- Security-sensitive changes must include a short risk note, even when the change is narrow.
- When fallback tooling is discussed, the fallback label must be explicit and the upstream path must still be named.
- Research claims about Remodex must distinguish:
  - upstream README evidence
  - installed package/source evidence
  - local runtime evidence
  - unproven assumptions
