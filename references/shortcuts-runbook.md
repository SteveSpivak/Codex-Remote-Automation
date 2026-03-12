# CRA Shortcuts Runbook

CRA uses iPhone Shortcuts as the operator-facing approval surface. The Shortcut belongs to the broker path first and the hybrid-native prototype second.

## Primary Broker Path

The Shortcut should receive a sanitized approval request derived from the App Server contract:

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

The Shortcut should return only:

```json
{
  "request_id": "<opaque approval callback id>",
  "decision": "accept | acceptForSession | decline | cancel"
}
```

## Suggested iPhone Shortcut Shape

1. Optional `Set VPN` or Tailscale-connect step
2. Show the approval summary and available decisions
3. Return the chosen decision to the local CRA broker over a private channel such as Tailscale + SSH
4. Surface explicit errors for stale requests, duplicate taps, or transport failures

The Shortcut should not decide how Codex is actuated locally. It should only return the decision to the broker.

## Fallback Prototype Path

The current repo still contains a fallback command path:

```bash
python3 -m cra.cli shortcut-entry --decision approve --action-id 11111111-1111-4111-8111-111111111111
```

That path exists only for the hybrid-native prototype in `cra/` and should be treated as fallback discovery tooling. It is not the canonical architecture.

## Failure Handling

- If VPN or SSH is unavailable, stop before sending the decision.
- If the broker reports a stale or unknown `request_id`, surface the error and do not retry blindly.
- If fallback prototype commands are used, clearly label the run as fallback in the operator notes or audit output.
