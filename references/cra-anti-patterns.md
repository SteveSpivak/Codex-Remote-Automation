# CRA Anti-Patterns

The following patterns are explicitly out of bounds for Codex Remote Automation (CRA).

## Protocol and Eventing

- Do not treat Codex log parsing as the primary approval source when App Server approval requests are available.
- Do not invent a second canonical approval contract alongside the App Server request and response identifiers.
- Do not resolve approvals without carrying `request_id` through to the final broker response.

## Network and Security

- Do not use router port forwarding, dynamic DNS, or any public-internet SSH exposure.
- Do not allow password-based SSH as a fallback.
- Do not let the mobile device reach broad portions of the tailnet when the workflow only needs to return a broker decision.

## UI Fallback

- Do not make AppleScript, Accessibility, OCR, or screenshot targeting the primary approval architecture.
- Do not target UI elements by screen coordinates, tab order, or fragile positional assumptions unless you are explicitly in fallback mode.
- Do not let fallback tooling drift into normal operations without updating the charter and standards.

## Repo and Workflow

- Do not leave repo docs claiming that watcher daemons, Pushcut/Pushover, or desktop-button clicks are the canonical architecture after the App Server pivot.
- Do not add a custom recurring scheduler when Codex automations and Triage are sufficient for the recurring check.
- Do not remove the human approval gate for convenience or perceived speed.
