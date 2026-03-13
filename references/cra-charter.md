# Project Charter: Codex Remote Automation (CRA)
**Version:** 2.0  
**Status:** Active  
**Owner:** Steve Spivak  
**Last updated:** 2026-03-13

---

## 1. Problem Statement

Codex can surface high-stakes approval points while working across files, commands, and long-running tasks. A human should be able to review and decide on those approvals from an iPhone without staying at the Mac and without relying on brittle desktop-button automation or ad hoc mobile shortcuts as the primary control plane.

Project CRA solves this by inserting a warm local CRA Bridge between Codex and the operator. The primary phone-compatible implementation now follows the Remodex transport model: the bridge consumes Codex approval events through `codex app-server`, synchronizes them over encrypted envelopes through a self-hosted relay, and returns the operator's decision back to Codex from a Remodex-compatible iPhone client.

---

## 2. Goals

| Goal | Measurable outcome |
|------|--------------------|
| Real-time Codex approval from iOS | Approve or decline any Codex approval request within 2 seconds of notification |
| Sub-0.5s feedback loop | iPhone tap -> broker response in < 500ms (P95) |
| Protocol-first control plane | Primary path uses App Server approval events, not GUI scraping or Shortcut-only glue |
| Transport-only relay | Relay routes encrypted envelopes and never sees approval plaintext |
| Zero exposed attack surface | No public-internet SSH; no managed relay dependency; no cloud-sync polling |
| Stable replay and validation | Approval transcripts can be replayed and tested with `codex exec --json` or App Server fixtures |

### Non-goals

- Building a general remote-control framework for arbitrary macOS apps
- Making desktop Accessibility or OCR the primary approval path
- Building a general mobile Codex chat client or Git workstation in v1
- Removing the human approval gate
- Supporting multiple simultaneous approvers in v1

---

## 3. Architecture

### 3.1 Topology

```text
Codex (macOS, App Server)
    ↓ JSON-RPC approval request
CRA Bridge (local, warm session)
    ↓ encrypted approval envelope
self-hosted relay (transport only)
    ↓ encrypted approval envelope
Remodex-compatible iPhone app
    ↓ encrypted decision envelope
self-hosted relay
    ↓ encrypted decision envelope
CRA Bridge
    ↓ JSON-RPC approval response
Codex continues
```

`codex exec --json` is the secondary surface for replay fixtures, contract validation, and long-horizon testing. Shortcuts, iMessage, and the existing Accessibility/OCR tooling remain available as fallback and discovery support only.

### 3.2 Canonical approval request

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

- `request_id` is the canonical response handle
- `thread_id`, `turn_id`, and `item_id` preserve Codex protocol identity for audit and replay
- `summary` must be sanitized before it is shown on the phone or logged

### 3.3 Canonical approval response

```json
{
  "request_id": "<opaque approval callback id>",
  "decision": "accept | acceptForSession | decline | cancel"
}
```

### 3.4 Bridge and mobile transport path

- The CRA Bridge keeps the local App Server session warm across phone disconnects
- The relay is self-hosted and transport-only: it can see session metadata, but not approval payload plaintext
- A Remodex-compatible iPhone app is the primary operator surface
- QR bootstrap is the default first-pairing mechanism; trusted reconnect is the default steady-state mechanism
- Shortcuts or iMessage may be used only as transitional fallback tooling when the Remodex app path is unavailable
- The transport returns a decision to the bridge; it does not drive the Codex desktop UI directly

### 3.5 Fallback path

- Accessibility, AppleScript, and OCR helpers are retained for discovery, emergency fallback, and protocol-gap investigation
- Fallback tooling may use `action_id`, `AXDescription`, or OCR text targeting within the prototype code under `cra/` and `references/discovery/`
- Fallback tooling must be explicitly labeled as fallback in documentation and operator runbooks

### 3.6 Explicitly rejected alternatives

| Alternative | Reason rejected |
|-------------|-----------------|
| Desktop-button automation as the primary architecture | Too brittle relative to App Server approval events |
| Codex log parsing as the primary approval source | Inferential and weaker than protocol-native approval requests |
| Managed relay dependency | Unnecessary trust boundary for a transport-only relay the operator can self-host |
| iCloud / Dropbox / Google Drive polling | Sync latency, collision risk, and poor auditability |
| Dynamic DNS + router port forward | Exposes the bridge or Mac to the public internet |
| Shortcut-only operator path as the long-term architecture | Too brittle and too constrained for pairing, reconnect, and encrypted session management |

---

## 4. Implementation Phases

### Phase 1 — Protocol foundation

- Validate `codex app-server` and `codex exec --json` surfaces locally
- Freeze the approval request and response contracts
- Align repo docs, skills, `AGENTS.md`, and `.codex` guidance around the App-Server-first model
- **Milestone:** repo guidance and contracts all reflect the protocol-first architecture

### Phase 2 — Bridge core

- Implement a local CRA Bridge core that connects to `codex app-server` over `stdio`
- Normalize approval requests, audit raw and sanitized events, and expose a mobile-safe request contract
- Add transcript fixtures and replay support
- **Milestone:** live approval request -> normalized bridge payload -> auditable local record

### Phase 3 — Secure bridge and relay

- Turn the local broker into a long-lived CRA Bridge with warm-session semantics
- Add QR bootstrap, trusted reconnect, encrypted envelopes, and replay protection
- Implement the self-hosted transport-only relay
- **Milestone:** pending approvals survive reconnect and relay plaintext exposure is eliminated

### Phase 4 — Mobile client compatibility

- Build and maintain Remodex-compatible mobile pairing, reconnect, pending approval sync, and decision submission
- Keep the response contract fixed to `request_id + decision`, with optional note for CRA-local audit only
- **Milestone:** paired Remodex-compatible iPhone app resolves the matching bridge request end-to-end

### Phase 5 — Fallback, QA, and hardening

- Keep Shortcuts, iMessage, Accessibility, and OCR as explicit fallback or discovery tooling
- Replay approval fixtures and reconnect scenarios with `codex exec --json` and App Server transcripts
- Exercise resilience scenarios: duplicate decisions, stale `request_id`, sleep/wake, relay reconnect, and revoked permissions
- **Milestone:** KPI targets met and replay evidence captured

Future recurring checks should use Codex automations and Triage when native automations are sufficient.

---

## 5. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| App Server protocol changes | Medium | High | Validate against `codex app-server --help` and shared contract docs before implementation |
| Decision replay or mismatch | Medium | High | Use `request_id` as the response handle and record the full request/response pair |
| Relay reconnect or phone handoff failure | Medium | High | Trusted reconnect, pending snapshot catch-up, and explicit stale-request handling |
| Pairing secret misuse | Low | High | Short QR expiry, bridge-side trust store, and key rotation |
| Broker and mobile payload drift | Medium | High | Single canonical request/response examples in shared docs and tests |
| Accessibility or OCR fallback drifts after Codex updates | High | Medium | Keep fallback isolated and clearly secondary |
| Managed or third-party relay compromise | Low | High | Self-host the relay and keep it blind to approval plaintext |

---

## 6. KPIs

| Metric | Target |
|--------|--------|
| Outbound notification latency (approval request -> phone visible) | < 2.0s |
| Inbound feedback latency (tap -> broker response) | < 500ms P95 |
| Relay plaintext exposure | 0 plaintext approval payloads visible to relay |
| Protocol/request mismatch rate | 0% |
| Replay fixture success rate | 100% on approved test corpus |
| Idle bridge overhead | < 1% CPU and < 50 MB RAM |
| Fallback activation frequency | Near-zero in normal operation |

---

## 7. Roles

| Role | Responsibility |
|------|---------------|
| CRA Orchestrator | Cross-skill routing, phase ordering, final contract assembly |
| Backend / Bridge Developer | App Server client, bridge runtime, JSON-RPC handling, transcript normalization, replay fixtures |
| macOS / Codex Environment Engineer | Repo `.codex` setup, App Server lifecycle, bridge residency, QR artifact generation, fallback Accessibility/OCR tooling |
| Networking & Mobile Architect | Self-hosted relay, native iOS client transport, pairing/reconnect UX, fallback Shortcuts when needed |
| Security Specialist | Bridge threat model, pairing and reconnect hardening, relay blindness, transcript integrity, approval authenticity |
| Test Engineer | Replay suites, pairing/reconnect validation, KPI evidence, fallback reliability checks |

---

## 8. Definition of Done

- [ ] App-Server-first CRA Bridge path implemented and documented
- [ ] Canonical request and response contracts aligned across docs, skills, and tests
- [ ] Self-hosted relay and encrypted session envelopes validated
- [ ] Native iPhone operator app resolves live approvals
- [ ] Replay fixtures and long-horizon validation evidence captured
- [ ] Transitional fallback tooling explicitly documented as secondary
- [ ] Repo-local Codex guidance (`AGENTS.md`, `.codex/`) checked in and aligned with the charter
