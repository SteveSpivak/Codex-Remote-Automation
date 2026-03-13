# CRA Secure Bridge Protocol

This document describes the primary CRA path after the Remodex-style pivot.

## Scope

The secure bridge protocol exists only to move approval requests and decisions between:

- the warm CRA Bridge on the Mac
- the self-hosted relay
- the native iPhone CRA Operator app

It does not replace the canonical approval contract. It wraps that contract in pairing, reconnect, and encrypted transport behavior.

## Step-By-Step Session Flow

1. Start the local relay.
2. Start or inspect the warm CRA Bridge on the Mac.
3. Generate a short-lived pairing payload with `bridge-create-pairing`.
4. Show the generated QR or pairing URI to the phone.
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

The bridge writes local runtime artifacts under `var/bridge/` by default:

- `device-state.json`: stable bridge device identity and trusted phones
- `pairing-payload.json`: current pairing payload for the active session
- `pairing-qr.txt`: QR stub or pairing URI helper
- `bridge-state.json`: current runtime status and pending approvals

Audit streams are written under `var/audit/` by default:

- `bridge-wire.jsonl`
- `bridge-events.jsonl`
- `broker-raw.jsonl`
- `broker-approvals.jsonl`
- `broker-decisions.jsonl`
- `broker-resolutions.jsonl`

## Pairing And Reconnect Rules

- QR bootstrap secrets expire quickly and are single-session bootstrap material.
- Trusted reconnect uses bridge-side device trust, not a new approval contract.
- The bridge is responsible for replay protection.
- Pending approvals must survive reconnects and be re-sent through a snapshot update.

## Fallback Boundary

Shortcuts, iMessage, Accessibility, AppleScript, and OCR are outside the primary secure bridge protocol.

They remain available only as:

- transitional operator tooling
- discovery tooling
- emergency fallback paths
