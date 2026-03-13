# CRA Secure Bridge Protocol

This document now describes CRA's compatibility and wrapper expectations around the upstream Remodex transport model. It is not a license to replace the upstream bridge before the upstream path is proven.

## Scope

The secure bridge protocol exists only to move approval requests and decisions between:

- the upstream Remodex bridge or an explicitly approved CRA wrapper on the Mac
- the selected relay path, which may be hosted or self-hosted depending on the current evidence
- the official Remodex iPhone app

It does not replace the canonical approval contract. It wraps that contract in pairing, reconnect, and encrypted transport behavior.

## Step-By-Step Session Flow

1. Start or inspect the upstream bridge on the Mac.
2. Start the selected relay path.
3. Generate a short-lived pairing payload with the upstream bridge or approved CRA wrapper.
4. Show the generated QR or pairing JSON to the phone.
5. The phone scans the pairing payload and opens a relay session as `role=iphone`.
6. The phone sends `clientHello`.
7. The bridge validates the QR bootstrap or trusted reconnect proof and replies with `serverHello`.
8. The phone sends `clientAuth`.
9. The bridge marks the phone trusted for future reconnects and replies with `secureReady`.
10. The phone sends `resumeState` with the last applied outbound sequence.
11. The bridge replays any buffered encrypted envelopes the phone missed.
12. When Codex emits an approval request, the bridge normalizes it and sends a `bridge/pendingApprovalsUpdated` notification inside an encrypted envelope.
13. The phone chooses `accept`, `acceptForSession`, `decline`, or `cancel`.
14. The phone sends `bridge/respondApproval` inside an encrypted envelope.
15. The bridge validates `request_id`, rejects stale or replayed input, and returns the approval response to Codex.

## Relay Contract

The relay is transport-only.

- It routes text WebSocket frames between `role=mac` and `role=iphone` peers in the same session.
- It can see session metadata such as session id and role.
- It must not receive approval payload plaintext.
- It must not decide, inspect, or rewrite approval requests.

## Bridge Artifacts

Current upstream evidence says the bridge persists device identity under `~/.remodex` and attempts Keychain-backed storage on macOS. CRA-specific wrapper or compatibility-study artifacts may also exist in repo-local locations such as `var/remodex-bridge/`, but those are not the baseline source of truth.

CRA audit streams are written under `var/audit/` by default:

- `bridge-wire.jsonl`
- `bridge-events.jsonl`
- `broker-raw.jsonl`
- `broker-approvals.jsonl`
- `broker-decisions.jsonl`
- `broker-resolutions.jsonl`

## Pairing And Reconnect Rules

- QR bootstrap payloads expire quickly and are single-session bootstrap material.
- Trusted reconnect uses bridge-side device trust, not a new approval contract.
- The bridge is responsible for replay protection.
- Pending approvals must survive reconnects and be re-sent through a snapshot update.

## Fallback Boundary

Shortcuts, iMessage, Accessibility, AppleScript, OCR, and the experimental in-repo CRA iOS client are outside the primary secure bridge protocol.

They remain available only as:

- transitional operator tooling
- discovery tooling
- emergency fallback paths
