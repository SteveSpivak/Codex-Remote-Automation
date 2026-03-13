# Project Charter: Codex Remote Automation (CRA)
**Version:** 2.1  
**Status:** Active  
**Owner:** Steve Spivak  
**Last updated:** 2026-03-13

---

## 1. Problem Statement

Codex surfaces high-stakes approval points while working across files, commands, and long-running tasks. A human should be able to review and decide on those approvals from an iPhone without staying at the Mac and without relying on brittle desktop-button automation.

CRA solves this by using `codex app-server` as the approval source and, for the current delivery strategy, proving the official Remodex bridge and iPhone app first. CRA then layers audit, policy, and operator guidance around that working baseline instead of prematurely reimplementing bridge or relay behavior.

---

## 2. Goals

| Goal | Measurable outcome |
|------|--------------------|
| Real-time Codex approval from iOS | Approve or decline any Codex approval request within 2 seconds of notification |
| Sub-0.5s feedback loop | iPhone tap -> broker response in < 500ms (P95) |
| Upstream-first delivery | Official `remodex` package proven before bridge or relay forking |
| Protocol-first control plane | Primary path uses App Server approval events, not GUI scraping or Shortcut-only glue |
| Stable replay and validation | Approval transcripts can be replayed and tested with `codex exec --json` or App Server fixtures |

### Non-goals

- Building a general remote-control framework for arbitrary macOS apps
- Making desktop Accessibility or OCR the primary approval path
- Reimplementing the full Remodex bridge or relay before upstream proof exists
- Building a general mobile Codex chat client or Git workstation in v1
- Removing the human approval gate
- Supporting multiple simultaneous approvers in v1

---

## 3. Architecture Strategy

### 3.1 Delivery Order

```text
Codex (macOS, App Server)
    ↓
official remodex bridge (`remodex up`)
    ↓
official Remodex iPhone app
    ↓
decision returned to Codex
```

CRA-specific additions come only after that baseline is proven:

```text
Codex
    ↓
upstream Remodex baseline
    ↓
CRA audit / policy / wrapper layer
    ↓
operator reporting and replay evidence
```

### 3.2 Canonical Approval Request

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

### 3.3 Canonical Approval Response

```json
{
  "request_id": "<opaque approval callback id>",
  "decision": "accept | acceptForSession | decline | cancel"
}
```

### 3.4 Upstream-First Rules

- The official `remodex` package is the primary bridge baseline.
- The official Remodex iPhone app is the primary mobile client baseline.
- The in-repo `remodex/` folder is a compatibility study and experiment, not the canonical implementation path.
- The relay path must be treated as unproven until the phone completes a known-good pair and approval round-trip in the target environment.
- CRA may wrap, observe, and audit upstream behavior before it forks it.

### 3.5 Decision Gate For Forking

Fork the minimum surface necessary only if one of these becomes true:

- upstream bridge behavior cannot satisfy a required approval audit or policy requirement
- upstream relay assumptions violate a hard project constraint
- the iPhone app blocks the required deployment model
- an unsupported extension point is required and cannot be added through wrapping

### 3.6 Fallback Paths

- Shortcuts, iMessage, Accessibility, AppleScript, and OCR remain fallback or discovery tools only
- Fallback tooling may use `action_id`, `AXDescription`, or OCR targeting inside the prototype code under `cra/` and `references/discovery/`
- Fallback tooling must be explicitly labeled fallback in documentation and reports

---

## 4. Research Priorities

1. Confirm upstream package commands, env vars, and state paths
2. Confirm whether self-hosted local relay is officially viable or only theoretically possible
3. Confirm whether the iPhone app requires `wss://` or hosted relay semantics
4. Confirm push and notification dependencies for a complete approval flow
5. Confirm which CRA requirements truly need a wrapper and which would force a fork

---

## 5. Implementation Phases

### Phase 1 — Upstream Proof

- Validate `remodex up`, `remodex resume`, and `remodex watch`
- Capture env vars, state paths, and runtime behavior
- Complete a known-good phone pairing and relay connection
- **Milestone:** upstream bridge and phone app are proven in the target environment

### Phase 2 — CRA Wrapper

- Add thin CRA audit, policy, and operator-facing guidance around upstream behavior
- Preserve the canonical request and response contracts
- Add replay and local validation around upstream outputs
- **Milestone:** upstream bridge plus CRA wrapper produces auditable approval evidence

### Phase 3 — Relay Decision

- Decide whether hosted relay use is acceptable for the project
- If not acceptable, fork the minimum relay or bridge surface required
- Keep the fork narrow and evidence-based
- **Milestone:** hosted-vs-self-hosted decision is locked with evidence

### Phase 4 — Hardening And Fallback

- Add reconnect, duplicate-decision, stale-request, and resilience checks
- Keep Shortcuts, iMessage, Accessibility, and OCR as explicit fallback only
- **Milestone:** KPI targets and proof matrix met

---

## 6. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Upstream app requires hosted relay semantics | Medium | High | Prove the official path before self-hosting work |
| iPhone app rejects local `ws://` relay | Medium | High | Validate `wss://` and ATS expectations before relay fork |
| Premature bridge fork drifts from upstream behavior | High | High | Upstream-first rule plus explicit fork gate |
| Decision replay or mismatch | Medium | High | Use `request_id` as the response handle and record the full request/response pair |
| Hosted relay risk exceeds project constraints | Medium | High | Security review and minimal fork decision gate |
| Fallback tooling becomes normal path | High | Medium | Keep fallback isolated and explicitly labeled |

---

## 7. KPIs

| Metric | Target |
|--------|--------|
| Outbound notification latency (approval request -> phone visible) | < 2.0s |
| Inbound feedback latency (tap -> broker response) | < 500ms P95 |
| Protocol/request mismatch rate | 0% |
| Replay fixture success rate | 100% on approved test corpus |
| Idle wrapper overhead | < 1% CPU and < 50 MB RAM |
| Fallback activation frequency | Near-zero in normal operation |

---

## 8. Roles

| Role | Responsibility |
|------|---------------|
| CRA Orchestrator | Cross-skill routing, evidence ordering, and fork-gate enforcement |
| CRA Upstream Integration | Package-fit evaluation, extension points, wrap-vs-fork decisions, and upgrade policy |
| Backend / Wrapper Developer | CRA audit, policy, transcript normalization, replay fixtures, and wrapper logic around upstream outputs |
| macOS / Codex Environment Engineer | Remodex install, env vars, local state, `.codex`, launchd, and fallback tooling |
| Networking & Mobile Architect | Relay viability, TLS, hosted-vs-self-hosted decision work, and iPhone connectivity |
| Security Specialist | Trust boundaries, state storage, relay blindness, hosted-vs-self-hosted risk, and approval authenticity |
| Test Engineer | Upstream proof matrix, reconnect validation, KPI evidence, and fallback reliability checks |

---

## 9. Definition of Done

- [ ] Upstream `remodex` path proven with a real phone pairing
- [ ] Canonical request and response contracts aligned across docs, skills, and tests
- [ ] Hosted-vs-self-hosted decision made with explicit evidence
- [ ] CRA wrapper responsibilities separated from upstream bridge ownership
- [ ] Replay fixtures and validation evidence captured
- [ ] Transitional fallback tooling explicitly documented as secondary
- [ ] Repo-local Codex guidance (`AGENTS.md`, `.codex/`) aligned with the upstream-first strategy
