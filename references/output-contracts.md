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

## Orchestrator Output

The orchestrator should assemble final delivery using these sections:

- Goal
- Primary protocol path
- Fallback path, if any
- Files or artifacts created or changed
- Commands or checks run
- Risks and constraints
- Validation and next checks

## Specialist Deliverables

Each specialist output should be concrete enough to hand to an implementer without extra routing work.

- `cra-backend-developer`: broker process shape, App Server event handling, approval contract mapping, replay fixtures, and transcript handling
- `cra-macos-engineer`: `.codex` project guidance, App Server lifecycle commands, local environment recovery, and fallback UI tooling guidance
- `cra-network-architect`: iPhone Shortcut flow, private decision transport, SSH/Tailscale constraints, and off-network validation
- `cra-security-specialist`: broker threat model, transport hardening, transcript integrity checks, and approval authenticity findings
- `cra-test-engineer`: replay corpus, decision-matrix tests, resilience scenarios, KPI evidence, and fallback reliability findings

## Delivery Rules

- Every output must state assumptions when the environment is not yet verified.
- Commands should be copyable as written and scoped to the minimum necessary privileges.
- Validation must include at least one protocol-path or replay-path check relevant to the subsystem.
- Risks should call out concrete breakpoints such as stale `request_id`, transport outages, revoked permissions, or protocol drift.
- Outputs must identify which path they apply to: `app_server`, `noninteractive_replay`, `accessibility_fallback`, or `vision_ocr_fallback`.
