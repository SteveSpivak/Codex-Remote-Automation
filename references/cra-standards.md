# CRA Standards

These standards apply to all Codex Remote Automation (CRA) planning and implementation work.

## Architecture Invariants

- Preserve the chartered topology: Codex -> watcher -> notification service -> iPhone Shortcut -> Tailscale SSH -> macOS actuator.
- Keep the project human-in-the-loop. CRA may assist approval flow, but it must not bypass the human approval decision.
- Treat the project as remote approval for Codex only, not as a general-purpose macOS remote control framework.

## Security Baseline

- Do not expose the Mac to the public internet. Remote access must stay inside Tailscale.
- Use key-only SSH with Ed25519 keys and disable password authentication and root login.
- Sanitize every dynamic string before it is serialized to JSON, logged for debugging, or included in an SSH command path.
- Restrict Tailscale ACLs to the smallest allowed path: the iPhone node may reach only port 22 on the Codex Mac.

## Implementation Rules

- Prefer stable selectors such as `AXDescription` for UI actuation; do not key automation to screen position, index, or timing alone.
- Prefer macOS-native event sources such as FSEvents through `watchdog`; avoid timer-based polling when a native signal exists.
- Generate a fresh UUID4 `action_id` for every approval event and treat it as untrusted input everywhere else in the system.
- Keep launchd-managed components restartable and observable with explicit stdout or stderr log targets.

## Performance and Reliability Targets

- Outbound notification latency target: less than 2 seconds from event to device notification.
- Inbound approval latency target: less than 500 ms P95 from tap to Mac execution.
- Idle watcher overhead target: less than 1% CPU and less than 50 MB RAM.
- Design recovery for sleep/wake transitions, network changes, and revoked macOS permissions.

## Documentation Expectations

- Every subsystem deliverable must include validation steps, known failure modes, and recovery guidance.
- Security-sensitive changes must include a short threat or risk note, even when the change is narrow.
- When multiple specialists contribute to a flow, the orchestrator output is the final contract for the combined deliverable.
