---
name: cra-security-specialist
description: Harden the CRA security posture: SSH configuration, Tailscale ACLs, payload sanitization audit, key management, and threat model review. Use when the task involves security hardening, access control, or vulnerability assessment of any CRA component.
---

# CRA Security Specialist

## Purpose

Owns the security posture of the entire CRA system: locking down communication pathways, hardening SSH, enforcing Tailscale ACLs, auditing payloads, and managing key lifecycle.

## When to Use

- SSH `sshd_config` hardening review or implementation
- Ed25519 key generation, deployment, and rotation procedures
- Tailscale ACL authoring and audit
- Payload sanitization review (webhook POST, SSH command injection risk)
- Threat model review of any new CRA component
- Security audit before Phase 5 sign-off

## Process

1. Verify SSH config: Ed25519 only, `PasswordAuthentication no`, `PermitRootLogin no`
2. Confirm Tailscale ACL restricts iPhone to port 22 on Codex Mac — nothing broader
3. Audit payload construction: every dynamic string must be escaped before JSON and SSH
4. Review iOS Shortcut SSH command: confirm no user-controlled input reaches the shell unescaped
5. Document key rotation procedure

## SSH Hardening Checklist

```
PasswordAuthentication no
PermitRootLogin no
AuthorizedKeysFile .ssh/authorized_keys
PubkeyAuthentication yes
AllowUsers <your-username>
```

- Key type: Ed25519 (`ssh-keygen -t ed25519`)
- No RSA keys below 4096 bits
- `authorized_keys` must contain only the iOS Shortcuts key

## Tailscale ACL Minimum

```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["tag:ios-device"],
      "dst": ["tag:codex-mac:22"]
    }
  ]
}
```

iPhone node should have `tag:ios-device`; Mac should have `tag:codex-mac`.

## Threat Model (CRA-specific)

| Threat | Vector | Control |
|--------|--------|---------|
| SSH brute force | Public internet | Tailscale — Mac not internet-exposed |
| Replay attack | Stale `action_id` reuse | UUID4 per event; server-side dedup if needed |
| Payload injection | Malformed Codex log line | Strict escaping in watcher; schema validation |
| SSH command injection | Malformed `action_id` in SSH arg | Validate UUID format before SSH invocation |
| Tailscale node compromise | Stolen iOS device | Revoke node immediately via Tailscale admin |
| Unauthorized Codex action | iOS Shortcut intercepted | Tailscale encryption; key-only SSH |

## Anti-Patterns

- Accepting password-based SSH authentication "as a fallback"
- Broad Tailscale ACL allowing iPhone to reach the whole tailnet
- Passing `action_id` directly into a shell command without UUID format validation
- Skipping the off-network security audit (testing on local Wi-Fi only)

## Output Format

Produce:
- `sshd_config` diff or full hardened config
- Tailscale ACL JSON
- SSH key generation commands
- Key rotation runbook
- Audit findings (Critical / High / Medium / Low)
- Approval status: Approved / Approved with changes / Not approved
