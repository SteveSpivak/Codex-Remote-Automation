# CRA Output Contracts

The orchestrator and specialist skills use the following output contracts to keep multi-step CRA work consistent.

## Canonical Approval Request

```json
{
  "request_id": "<opaque approval callback id>",
  "thread_id": "<codex thread id>",
  "turn_id": "<codex turn id>",
  "item_id": "<approval item id>",
  "kind": "command_execution | file_change",
  "summary": "<sanitized operator-facing summary>",
  "available_decisions": ["accept", "acceptForSession", "decline", "cancel"],
  "timestamp": "<ISO8601>"
}
```

## Canonical Approval Response

```json
{
  "request_id": "<opaque approval callback id>",
  "decision": "accept | acceptForSession | decline | cancel"
}
```

`operator_note` may be carried by the native iOS app or other operator surface for CRA audit, but it is not part of the canonical Codex approval response sent back to App Server.

## Bridge Pairing Payload

```json
{
  "v": 2,
  "relay": "ws://relay.example:8787",
  "sessionId": "<bridge session id>",
  "macDeviceId": "<stable bridge device id>",
  "macIdentityPublicKey": "<Ed25519 public key>",
  "expiresAt": 1773333333000
}
```

This QR payload is encoded as raw JSON for the Remodex iPhone app to scan. The older CRA-specific shared-secret pairing payload remains legacy fallback code only and is not the primary mobile contract.

## Bridge Control Messages

These messages are relay-visible but must not contain approval plaintext:

```json
{
  "kind": "clientHello | serverHello | clientAuth | secureReady | resumeState",
  "sessionId": "<bridge session id>"
}
```

## Encrypted Session Envelope

```json
{
  "kind": "encryptedEnvelope",
  "v": 1,
  "sessionId": "<bridge session id>",
  "keyEpoch": 1,
  "sender": "mac | iphone",
  "counter": 42,
  "ciphertext": "<base64>",
  "tag": "<base64>"
}
```

## Pending Approval Sync Notification

```json
{
  "method": "bridge/pendingApprovalsUpdated",
  "params": {
    "pendingApprovals": [
      {
        "request_id": "<opaque approval callback id>",
        "thread_id": "<codex thread id>",
        "turn_id": "<codex turn id>",
        "item_id": "<approval item id>",
        "kind": "command_execution | file_change",
        "summary": "<sanitized operator-facing summary>",
        "available_decisions": ["accept", "acceptForSession", "decline", "cancel"],
        "timestamp": "<ISO8601>"
      }
    ],
    "pendingCount": 1,
    "updatedAt": "<ISO8601>"
  }
}
```

## Fallback Shortcut Operator Payload

```json
{
  "title": "CRA approval required",
  "subtitle": "command_execution | file_change",
  "request_id": "<opaque approval callback id>",
  "summary": "<sanitized operator-facing summary>",
  "decision_options": [
    {"value": "accept", "label": "Accept"},
    {"value": "acceptForSession", "label": "Accept for Session"},
    {"value": "decline", "label": "Decline"},
    {"value": "cancel", "label": "Cancel"}
  ],
  "default_decision": "decline",
  "operator_note_enabled": true,
  "operator_note_prompt": "Optional note for CRA audit"
}
```

This payload remains valid for the Shortcut fallback path, but it is no longer the primary operator interface.

## Orchestrator Output

The orchestrator should assemble final delivery using these sections:

- Goal
- Primary bridge path
- Fallback path, if any
- Files or artifacts created or changed
- Commands or checks run
- Risks and constraints
- Validation and next checks

## Specialist Deliverables

Each specialist output should be concrete enough to hand to an implementer without extra routing work.

- `cra-backend-developer`: bridge runtime shape, App Server event handling, approval contract mapping, reconnect snapshot handling, replay fixtures, and transcript handling
- `cra-macos-engineer`: `.codex` project guidance, App Server and bridge lifecycle commands, local environment recovery, and fallback UI tooling guidance
- `cra-network-architect`: relay and native iOS client flow, pairing/reconnect transport notes, fallback Shortcuts when needed, and validation steps
- `cra-security-specialist`: bridge threat model, pairing/replay protection, relay hardening, transcript integrity checks, and approval authenticity findings
- `cra-test-engineer`: replay corpus, decision-matrix tests, reconnect scenarios, KPI evidence, and fallback reliability findings

## Delivery Rules

- Every output must state assumptions when the environment is not yet verified.
- Commands should be copyable as written and scoped to the minimum necessary privileges.
- Validation must include at least one protocol-path or replay-path check relevant to the subsystem.
- Risks should call out concrete breakpoints such as stale `request_id`, relay reconnects, revoked permissions, or protocol drift.
- Outputs must identify which path they apply to: `bridge_secure_session`, `noninteractive_replay`, `shortcut_fallback`, `imessage_fallback`, `accessibility_fallback`, or `vision_ocr_fallback`.
