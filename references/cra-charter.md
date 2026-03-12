# Project Charter: Codex Remote Automation (CRA)
**Version:** 2.0  
**Status:** Active  
**Owner:** Steve Spivak  
**Last updated:** 2026-03-13

---

## 1. Problem Statement

Codex can surface high-stakes approval points while working across files, commands, and long-running tasks. A human should be able to review and decide on those approvals from an iPhone without staying at the Mac and without relying on brittle desktop-button automation as the primary control plane.

Project CRA solves this by inserting a local approval broker between Codex and the operator. The broker consumes Codex approval events through `codex app-server`, normalizes them into a mobile-safe contract, delivers them to the iPhone, and returns the operator's decision back to Codex over a private channel.

---

## 2. Goals

| Goal | Measurable outcome |
|------|--------------------|
| Real-time Codex approval from iOS | Approve or decline any Codex approval request within 2 seconds of notification |
| Sub-0.5s feedback loop | iPhone tap -> broker response in < 500ms (P95) |
| Protocol-first control plane | Primary path uses App Server approval events, not GUI scraping |
| Zero exposed attack surface | No open router ports; no public-internet SSH; no cloud-sync polling |
| Stable replay and validation | Approval transcripts can be replayed and tested with `codex exec --json` or App Server fixtures |

### Non-goals

- Building a general remote-control framework for arbitrary macOS apps
- Making desktop Accessibility or OCR the primary approval path
- Removing the human approval gate
- Supporting multiple simultaneous approvers in v1

---

## 3. Architecture

### 3.1 Topology

```text
Codex (macOS, App Server)
    ↓ JSON-RPC approval request
CRA broker (local)
    ↓ sanitized mobile approval payload
iPhone approval surface
    ↓ private decision transport (Tailscale SSH or equivalent)
CRA broker
    ↓ JSON-RPC approval response
Codex continues
```

`codex exec --json` is the secondary surface for replay fixtures, contract validation, and long-horizon testing. The existing Accessibility/OCR tooling remains available as fallback and discovery support only.

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

### 3.4 Mobile and transport path

- iPhone Shortcuts remains the primary operator surface
- Tailscale and SSH remain acceptable private return channels when the decision needs to reach the local broker from off-network
- Third-party notification relays such as Pushcut or Pushover are optional adapters, not the canonical architecture
- The transport returns a decision to the broker; it does not drive the Codex desktop UI directly

### 3.5 Fallback path

- Accessibility, AppleScript, and OCR helpers are retained for discovery, emergency fallback, and protocol-gap investigation
- Fallback tooling may use `action_id`, `AXDescription`, or OCR text targeting within the prototype code under `cra/` and `references/discovery/`
- Fallback tooling must be explicitly labeled as fallback in documentation and operator runbooks

### 3.6 Explicitly rejected alternatives

| Alternative | Reason rejected |
|-------------|-----------------|
| Desktop-button automation as the primary architecture | Too brittle relative to App Server approval events |
| Codex log parsing as the primary approval source | Inferential and weaker than protocol-native approval requests |
| iCloud / Dropbox / Google Drive polling | Sync latency, collision risk, and poor auditability |
| Dynamic DNS + router port forward | Exposes the Mac to the public internet |
| Cloud relay as the only control plane | Adds an unnecessary trust boundary when local/private transport is available |

---

## 4. Implementation Phases

### Phase 1 — Protocol foundation

- Validate `codex app-server` and `codex exec --json` surfaces locally
- Freeze the approval request and response contracts
- Align repo docs, skills, `AGENTS.md`, and `.codex` guidance around the App-Server-first model
- **Milestone:** repo guidance and contracts all reflect the protocol-first architecture

### Phase 2 — Broker core

- Implement a local CRA broker that connects to `codex app-server` over `stdio`
- Normalize approval requests, audit raw and sanitized events, and expose a mobile-safe request contract
- Add transcript fixtures and replay support
- **Milestone:** live approval request -> normalized broker payload -> auditable local record

### Phase 3 — Mobile decision transport

- Build the iPhone Shortcut flow around the canonical request and response contracts
- Return decisions to the broker over Tailscale/SSH or another private transport
- Handle duplicate taps, stale requests, and transport failures explicitly
- **Milestone:** phone decision resolves the matching broker request end-to-end

### Phase 4 — Fallback and discovery

- Maintain the existing Accessibility/OCR tooling for discovery and emergency fallback
- Keep selector notes, screenshot captures, and OCR findings current when Codex UI changes
- Do not promote the fallback path over the broker path
- **Milestone:** visible approval prompt can be inspected or actuated only if the primary path is unavailable

### Phase 5 — QA, automations, and hardening

- Replay approval fixtures with `codex exec --json` and App Server transcripts
- Exercise resilience scenarios: duplicate decisions, stale `request_id`, sleep/wake, VPN drops, revoked permissions
- Document how recurring checks should use Codex automations and Triage when native automations are sufficient
- **Milestone:** KPI targets met and replay evidence captured

---

## 5. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| App Server protocol changes | Medium | High | Validate against `codex app-server --help` and shared contract docs before implementation |
| Decision replay or mismatch | Medium | High | Use `request_id` as the response handle and record the full request/response pair |
| Private return transport unavailable off-network | Medium | Medium | Tailscale health checks, retry logic, and explicit operator-visible errors |
| Broker and mobile payload drift | Medium | High | Single canonical request/response examples in shared docs and tests |
| Accessibility or OCR fallback drifts after Codex updates | High | Medium | Keep fallback isolated and clearly secondary |
| Third-party notification adapter downtime | Low | Medium | Keep the broker and transport contract independent of any single notification provider |

---

## 6. KPIs

| Metric | Target |
|--------|--------|
| Outbound notification latency (approval request -> phone visible) | < 2.0s |
| Inbound feedback latency (tap -> broker response) | < 500ms P95 |
| Protocol/request mismatch rate | 0% |
| Replay fixture success rate | 100% on approved test corpus |
| Idle broker overhead | < 1% CPU and < 50 MB RAM |
| Fallback activation frequency | Near-zero in normal operation |

---

## 7. Roles

| Role | Responsibility |
|------|---------------|
| CRA Orchestrator | Cross-skill routing, phase ordering, final contract assembly |
| Backend / Broker Developer | App Server client, JSON-RPC handling, transcript normalization, replay fixtures |
| macOS / Codex Environment Engineer | Repo `.codex` setup, App Server lifecycle, fallback Accessibility/OCR tooling |
| Networking & Mobile Architect | iPhone Shortcut flow, Tailscale/SSH decision delivery, optional notification adapters |
| Security Specialist | Broker threat model, transport hardening, transcript integrity, approval authenticity |
| Test Engineer | Replay suites, resilience validation, KPI evidence, fallback reliability checks |

---

## 8. Definition of Done

- [ ] App-Server-first approval broker path implemented and documented
- [ ] Canonical request and response contracts aligned across docs, skills, and tests
- [ ] Private transport validated off-network
- [ ] Replay fixtures and long-horizon validation evidence captured
- [ ] Fallback Accessibility/OCR tooling explicitly documented as secondary
- [ ] Repo-local Codex guidance (`AGENTS.md`, `.codex/`) checked in and aligned with the charter
