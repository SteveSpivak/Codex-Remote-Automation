# CRA Anti-Patterns

The following patterns are explicitly out of bounds for Codex Remote Automation (CRA).

## Upstream And Architecture

- Do not treat source availability as proof that self-hosting is already a supported production path.
- Do not reimplement the full bridge or relay before proving the upstream `remodex` path in the target environment.
- Do not keep repo docs claiming that the in-repo `remodex/` compatibility study is the canonical implementation path.
- Do not invent a second canonical approval contract alongside the App Server request and response identifiers.

## Network And Mobile

- Do not assume a plain local `ws://` relay is equivalent to the hosted upstream relay path without phone-side proof.
- Do not hardcode the Mac's local IP address into the long-term architecture.
- Do not treat the relay as a business-logic service that inspects approval plaintext.
- Do not let Shortcuts or iMessage remain framed as the primary operator surface after the upstream-first pivot.

## Security

- Do not treat the hosted-vs-self-hosted relay decision as cosmetic.
- Do not allow approval responses without `request_id`.
- Do not rely on screenshots or OCR as an audit source for normal operations.
- Do not let fallback UI automation drift into normal operations without explicit architecture change approval.

## Workflow

- Do not wait for a full custom implementation before proving the upstream package behavior.
- Do not claim self-hosted relay viability without naming the evidence source.
- Do not add a custom recurring scheduler when Codex automations and Triage are sufficient for the recurring check.
