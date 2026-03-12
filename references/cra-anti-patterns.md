# CRA Anti-Patterns

The following patterns are explicitly out of bounds for Codex Remote Automation (CRA).

## Network and Security

- Do not use router port forwarding, dynamic DNS, or any public-internet SSH exposure.
- Do not allow password-based SSH as a fallback.
- Do not give the iPhone node broad Tailscale access to the full tailnet when the workflow needs only port 22 on the Codex Mac.

## Eventing and Transport

- Do not use iCloud, Dropbox, Google Drive, or any file-sync channel as the approval transport.
- Do not poll Codex output on a timer when FSEvents or another native change signal is available.
- Do not send raw Codex log lines directly to a webhook, notification service, or shell command.

## UI Automation

- Do not target UI elements by screen coordinates, tab order, or fragile positional assumptions.
- Do not assume Accessibility permissions remain valid across macOS upgrades or app updates.
- Do not let actuator failures fail silently; they must log a recoverable error path.

## System Scope

- Do not expand CRA into a generic remote desktop or arbitrary application controller.
- Do not remove the human approval gate for convenience or performance.
- Do not optimize for local Wi-Fi-only success; the system must be validated off-network.
