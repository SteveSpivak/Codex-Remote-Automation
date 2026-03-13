# CRA Anti-Patterns

The following patterns are explicitly out of bounds for Codex Remote Automation (CRA).

## Protocol and Eventing

- Do not treat Codex log parsing as the primary approval source when App Server approval requests are available.
- Do not invent a second canonical approval contract alongside the App Server request and response identifiers.
- Do not resolve approvals without carrying `request_id` through to the final broker response.
- Do not let the relay become an approval-aware service that inspects or rewrites payload plaintext.

## Network and Security

- Do not use router port forwarding, dynamic DNS, or any public-internet SSH exposure.
- Do not allow password-based SSH as a fallback.
- Do not depend on a managed relay when the architecture requires a self-hosted transport-only relay.
- Do not let the mobile device or relay gain broader network reach than the approval workflow requires.

## UI Fallback

- Do not make AppleScript, Accessibility, OCR, or screenshot targeting the primary approval architecture.
- Do not target UI elements by screen coordinates, tab order, or fragile positional assumptions unless you are explicitly in fallback mode.
- Do not let fallback tooling drift into normal operations without updating the charter and standards.
- Do not keep Shortcuts or iMessage framed as the primary operator surface after the Remodex bridge pivot.

## Repo and Workflow

- Do not leave repo docs claiming that Shortcuts, iMessage, watcher daemons, Pushcut/Pushover, or desktop-button clicks are the canonical architecture after the bridge pivot.
- Do not add a custom recurring scheduler when Codex automations and Triage are sufficient for the recurring check.
- Do not remove the human approval gate for convenience or perceived speed.
